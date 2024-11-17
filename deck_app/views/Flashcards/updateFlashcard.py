from rest_framework.decorators import api_view
from django.http import JsonResponse
from ...serializers_flashcard import FlashCardGetSerializer
from rest_framework import status
from django.views.decorators.csrf import csrf_exempt
from ...models import Deck, DeckFlashCard, UserFlashCard, FlashCard, DeckFlashcardExample, DeckFlashcardTranslation, DeckFlashcardPronunciation
from ...models import Example, Translation, Pronunciation, FlashcardPhoto, FlashCardPriority
from ...validation.validation_jwt import validate_jwt
from django.db import transaction
import re
from .create_flashcard import upload_audio_from_url_to_firebase
from rest_framework.exceptions import ValidationError


@csrf_exempt
@api_view(['PUT'])
def update_flashcard(request, flashcardId, deckId):
    if request.method == "PUT":
        try:
            # Obtenção do token JWT e validação do usuário
            token = request.headers.get('Authorization')
            if not token:
                return JsonResponse({
                    'success': False,
                    'error': ['Token de autorização ausente. Faça login novamente.']
                }, status=status.HTTP_401_UNAUTHORIZED)

            jwt_data = validate_jwt(token)
            user_id = jwt_data.get('id')

            # Validação do deck
            deck = Deck.objects.get(id=deckId)
            if deck.type_deck == "Standard":
                return JsonResponse({
                    "success": False,
                    "error": ["Você não tem permissão para alterar este flashcard"]
                }, status=status.HTTP_403_FORBIDDEN)

            # Validação do flashcard associado ao deck
            deck_flashcard = DeckFlashCard.objects.get(
                flashcard_id=flashcardId, deck_id=deckId)
            flashcard = FlashCard.objects.get(
                id=flashcardId)

            with transaction.atomic():
                user_flashcards_count = UserFlashCard.objects.filter(
                    deck_flashcard_id=deck_flashcard.id).count()
                if user_flashcards_count > 1:
                    create_new_flashcard = True
                else:
                    create_new_flashcard = False

                if create_new_flashcard:
                    old_user_flashcard = UserFlashCard.objects.filter(
                        deck_flashcard_id=deck_flashcard.id,
                        user_id=user_id).first()

                    old_user_flashcard_id = old_user_flashcard.id

                    old_flashcard_priority = FlashCardPriority.objects.filter(
                        user_flashcard_id=old_user_flashcard.id,
                        user_id=user_id).first()
                    old_flashcard_priority_id = old_flashcard_priority.id
                    new_flashcard = FlashCard.objects.create(
                        **{field.name: getattr(flashcard, field.name) for field in FlashCard._meta.fields if field.name != 'id'})

                    serializer_deck_flashcard = DeckFlashCard.objects.create(
                        flashcard=new_flashcard, deck=deck_flashcard.deck)
                    UserFlashCard.objects.create(
                        deck_flashcard=serializer_deck_flashcard,
                        user_id=user_id,
                        one_star=old_user_flashcard.one_star,
                        two_stars=old_user_flashcard.two_stars,
                        three_stars=old_user_flashcard.three_stars,
                        four_stars=old_user_flashcard.four_stars,
                        five_stars=old_user_flashcard.five_stars,
                        last_time=old_user_flashcard.last_time,
                        last_feedback=old_user_flashcard.last_feedback)

                    FlashCardPriority.objects.create(
                        deck_flashcard=new_flashcard,
                        user_id=user_id,
                        priority=old_flashcard_priority.priority,
                        date_to_study=old_flashcard_priority.date_to_study
                    )

                    UserFlashCard.objects.filter(
                        id=old_user_flashcard_id).delete()
                    FlashCardPriority.objects.filter(
                        id=old_flashcard_priority_id).delete()

                    deck_flashcard = serializer_deck_flashcard
                    flashcard = new_flashcard

                word_wrong = update_flashcard_data(flashcard, request.data)
                if word_wrong is False:
                    return JsonResponse({'success': False,
                                         'error': ['Palavra não encontrada na frase']},
                                        status=status.HTTP_400_BAD_REQUEST)

                existing_examples, new_examples, exist_example = process_ex(
                    request.data.get('examples', []), deck_flashcard)
                existing_pr, new_prs, exist_pr = process_pr(
                    request.data.get('pronunciations', []), deck_flashcard)
                existing_tr, new_trs, tr_exist_ids = process_tr(
                    request.data.get('translations', []), deck_flashcard)
                img_ids_to_keep, img_ids_to_add = process_img(
                    request.data.get('images', []), deck_flashcard)

                if new_examples:
                    Example.objects.bulk_create(new_examples)
                    for new_example in new_examples:
                        existing_example = Example.objects.filter(
                            text_example=new_example.text_example).first()
                        if existing_example:
                            existing_examples.add(existing_example.id)
                            exist_example.add(existing_example.id)

                if new_trs:
                    Translation.objects.bulk_create(new_trs)
                    for new_tr in new_trs:
                        existing_trs = Translation.objects.filter(
                            text_translation=new_tr.text_translation).first()
                        if existing_trs:
                            existing_tr.add(existing_trs.id)
                            tr_exist_ids.add(existing_trs.id)
                if existing_pr:
                    link_pr_to_deck_flashcard(
                        existing_pr, deck_flashcard)

                if existing_examples:
                    link_examples_to_deck_flashcard(
                        existing_examples, deck_flashcard)

                if existing_tr:
                    link_tr_to_deck_flashcard(
                        existing_tr, deck_flashcard)

                remove_old_examples(deck_flashcard, exist_example)
                remove_old_pr(deck_flashcard, exist_pr)
                remove_old_tr(deck_flashcard, tr_exist_ids)
                remove_old_img(deck_flashcard, img_ids_to_keep)

            # Se a transação foi bem-sucedida
            return JsonResponse({
                "success": True,
                "message": ["Flashcard atualizado com sucesso."]
            }, status=status.HTTP_200_OK)

        except DeckFlashCard.DoesNotExist:
            return JsonResponse({'success': False,
                                 'error': ['DeckFlashCard não encontrado.']},
                                status=status.HTTP_404_NOT_FOUND)
        except FlashCard.DoesNotExist:
            return JsonResponse({'success': False,
                                 'error': ['FlashCard não encontrado.']},
                                status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return JsonResponse({'success': False,
                                 'error': f'Erro: {str(e)}'},
                                status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    else:
        return JsonResponse({"success": False,
                             "error": ["Método não autorizado"]},
                            status=status.HTTP_405_METHOD_NOT_ALLOWED)


def remove_old_examples(deck_flashcard, exist_ids):
    current_example_ids = DeckFlashcardExample.objects.filter(
        deck_flashcard=deck_flashcard).values_list('example_id', flat=True)

    examples_to_remove = set(current_example_ids) - set(exist_ids)

    DeckFlashcardExample.objects.filter(
        example_id__in=examples_to_remove,
        deck_flashcard=deck_flashcard).delete()


def remove_old_pr(deck_flashcard, exist_pr_ids):
    """Remove as relações intermediárias antigas de pronunciations que não estão mais presentes."""
    current_pr_ids = DeckFlashcardPronunciation.objects.filter(
        deck_flashcard=deck_flashcard).values_list('pronunciation_id', flat=True)

    # Encontrar as relações para remover (que não estão mais presentes)
    pr_to_remove = set(current_pr_ids) - set(exist_pr_ids)

    if pr_to_remove:
        DeckFlashcardPronunciation.objects.filter(
            pronunciation_id__in=pr_to_remove,
            deck_flashcard=deck_flashcard).delete()


def remove_old_tr(deck_flashcard, exist_tr_ids):
    current_tr_ids = DeckFlashcardTranslation.objects.filter(
        deck_flashcard=deck_flashcard).values_list(
            'translation_id', flat=True)
    tr_to_remove = set(current_tr_ids) - set(exist_tr_ids)
    DeckFlashcardTranslation.objects.filter(
        translation_id__in=tr_to_remove,
        deck_flashcard=deck_flashcard).delete()


def remove_old_img(deck_flashcard, exist_img_urls):
    current_img_urls = FlashcardPhoto.objects.filter(
        deck_flashcard=deck_flashcard
    ).values_list('file_url', flat=True)
    print(exist_img_urls)
    print(current_img_urls)
    img_to_remove = set(current_img_urls) - set(exist_img_urls)
    print(img_to_remove)
    if img_to_remove:
        FlashcardPhoto.objects.filter(
            file_url__in=img_to_remove,
            deck_flashcard=deck_flashcard).delete()


def process_img(existing_images, deck_flashcard):
    img_ids_to_keep = set()
    img_ids_to_add = []

    for image_data in existing_images:
        img_id = image_data.get('id')
        img_url = image_data.get('imageUrl')
        img_description = image_data.get('description', "")

        # Caso o 'id' seja válido e não seja 0
        if img_id and img_id != 0:
            img = FlashcardPhoto.objects.filter(
                file_url=img_url,
                file_description=img_description).first()

            if img:
                # Se a imagem já existe, adiciona a URL ao conjunto de imagens a manter
                img_ids_to_keep.add(img.file_url)
            else:
                # Caso contrário, adiciona a imagem para ser criada
                img_ids_to_add.append(FlashcardPhoto(
                    deck_flashcard_id=deck_flashcard.id,
                    file_url=img_url,
                    file_description=img_description
                ))
        else:
            # Se não for um 'id' válido, ainda verificamos se a imagem já existe
            img = FlashcardPhoto.objects.filter(
                file_url=img_url,
                file_description=img_description).first()
            if img:
                img_ids_to_keep.add(img.file_url)
            else:
                img_ids_to_add.append(FlashcardPhoto(
                    deck_flashcard_id=deck_flashcard.id,
                    file_url=img_url,
                    file_description=img_description
                ))

    # Cria as imagens em massa (bulk_create), evitando duplicações
    if img_ids_to_add:
        FlashcardPhoto.objects.bulk_create(img_ids_to_add)

        # Depois de criar as imagens, adiciona suas URLs ao conjunto de imagens a manter
        for image in img_ids_to_add:
            existing_img = FlashcardPhoto.objects.filter(
                file_url=image.file_url).first()
            if existing_img:
                print(existing_img.file_url)
                img_ids_to_keep.add(existing_img.file_url)
    print(img_ids_to_keep)
    return img_ids_to_keep, img_ids_to_add


# def update_flashcard_data(flashcard, data):
    """Update flashcard data from request."""
    if 'flashcard' in data:
        flashcard_data = data['flashcard']
        flashcard_data['main_phrase'] = flashcard_data.pop('mainPhrase', None)

        # Obtém a keyword e a main_phrase
        keyword = flashcard_data.get('keyword')
        main_phrase = flashcard_data.get('main_phrase', '')

        if keyword:
            pattern = r'\b' + re.escape(keyword) + r'\b'
            if not re.search(pattern, main_phrase):
                return False

        # Cria o serializer e valida os dados
        serializer_flashcard = FlashCardGetSerializer(
            flashcard, data=flashcard_data, partial=True)

        if serializer_flashcard.is_valid():
            serializer_flashcard.save()
            return True  # Retorna True se a atualização foi bem-sucedida


def update_flashcard_data(flashcard, data):
    main_phrase = data.get('mainPhrase')
    keyword = data.get('keyword')

    if not main_phrase and not keyword:
        raise ValidationError(
            "É necessário fornecer 'mainPhrase' ou 'keyword'.")

    if keyword and main_phrase:
        pattern = r'\b' + re.escape(keyword) + r'\b'
        if not re.search(pattern, main_phrase):
            raise ValidationError(
                f"A keyword '{keyword}' não está presente na frase principal.")

    flashcard_data = {}

    # Se 'mainPhrase' foi fornecido, atualiza o campo
    if main_phrase:
        flashcard_data['main_phrase'] = main_phrase

    if keyword:
        flashcard_data['keyword'] = keyword

    try:
        serializer_flashcard = FlashCardGetSerializer(flashcard,
                                                      data=flashcard_data,
                                                      partial=True)

        if serializer_flashcard.is_valid():
            serializer_flashcard.save()
            return True
        else:
            raise ValidationError(f"Erro de validação: {serializer_flashcard.errors}")

    except Exception as e:
        # Caso ocorra um erro ao salvar, lança uma exceção
        raise ValidationError(f"Erro ao atualizar o flashcard: {str(e)}")


def handle_user_flashcards(deck_flashcard, flashcard, user_id):
    """Handle creation of new flashcards for the user."""
    user_flashcards_count = UserFlashCard.objects.filter(
        deck_flashcard_id=deck_flashcard.id).count()
    if user_flashcards_count > 1:
        new_flashcard_data = {field.name: getattr(
            flashcard, field.name) for field in FlashCard._meta.fields if field.name != 'id'}
        new_flashcard = FlashCard.objects.create(**new_flashcard_data)
        serializer_deck_flashcard = DeckFlashCard.objects.create(
            flashcard=new_flashcard, deck=deck_flashcard.deck)
        UserFlashCard.objects.create(
            deck_flashcard=serializer_deck_flashcard, user_id=user_id)


def process_ex(examples_data, deck_flashcard):
    """Process and categorize examples from request data."""
    existing_example_ids = set()
    exist_ids = set()
    new_examples = []

    for example_data in examples_data:
        example_id = example_data.get('id')
        example_text = example_data.get('textExample')

        if example_id and example_id != 0:
            existing_example = Example.objects.filter(id=example_id).first()
            if existing_example:
                verify = DeckFlashcardExample.objects.filter(
                    example_id=existing_example.id,
                    deck_flashcard_id=deck_flashcard.id)
                if not verify.exists():
                    existing_example_ids.add(existing_example.id)
                    exist_ids.add(existing_example.id)
                if verify.exists():
                    exist_ids.add(existing_example.id)
        else:
            example_exist = Example.objects.filter(
                text_example=example_text).first()
            if example_exist:
                verify = DeckFlashcardExample.objects.filter(
                    example_id=example_exist.id,
                    deck_flashcard_id=deck_flashcard.id)
                if not verify.exists():
                    existing_example_ids.add(example_exist.id)
                    exist_ids.add(example_exist.id)
                if verify.exists():
                    exist_ids.add(example_exist.id)
            else:
                new_examples.append(Example(text_example=example_text))

    return existing_example_ids, new_examples, exist_ids


def process_tr(tr_data, deck_flashcard):
    existing_tr_ids = set()
    tr_exist_ids = set()
    new_trs = []

    for translation_data in tr_data:
        tr_id = translation_data.get('id')
        tr_text = translation_data.get('textTranslation')

        if tr_id and tr_id != 0:
            existing_tr = Translation.objects.filter(id=tr_id).first()
            if existing_tr:
                verify = DeckFlashcardTranslation.objects.filter(
                    translation_id=existing_tr.id,
                    deck_flashcard_id=deck_flashcard.id)
                if not verify.exists():
                    existing_tr_ids.add(existing_tr.id)
                    tr_exist_ids.add(existing_tr.id)
                if verify.exists():
                    tr_exist_ids.add(existing_tr.id)
        else:
            tr_exist = Translation.objects.filter(
                text_translation=tr_text).first()
            if tr_exist:
                verify = DeckFlashcardTranslation.objects.filter(
                    translation_id=tr_exist.id,
                    deck_flashcard_id=deck_flashcard.id)
                if not verify.exists():
                    existing_tr_ids.add(tr_exist.id)
                    tr_exist_ids.add(tr_exist.id)
                if verify.exists():
                    tr_exist_ids.add(tr_exist.id)
            else:
                new_trs.append(Translation(text_translation=tr_text))

    return existing_tr_ids, new_trs, tr_exist_ids


def process_pr(pr_data, deck_flashcard):
    existing_pr_ids = set()
    pr_exist_ids = set()
    new_prs = []

    for pronunciation_data in pr_data:
        pr_id = pronunciation_data.get('id')
        pr_text = pronunciation_data.get('keyword')
        pr_link = pronunciation_data.get('audioUrl')
        country = pronunciation_data.get('country')
        sex = pronunciation_data.get('sex')
        voice_name = pronunciation_data.get('voiceName')

        if pr_id and pr_id != 0:
            # Se já existe um ID de pronúncia fornecido, tentamos associá-lo
            existing_pr = Pronunciation.objects.filter(id=pr_id).first()
            if existing_pr:
                verify = DeckFlashcardPronunciation.objects.filter(
                    pronunciation_id=existing_pr.id,
                    deck_flashcard_id=deck_flashcard.id)
                if not verify.exists():
                    # Adiciona o ID da pronúncia existente
                    existing_pr_ids.add(existing_pr.id)
                    pr_exist_ids.add(existing_pr.id)
        else:
            # Caso contrário, verificamos se a combinação de 'keyword' e 'audio_url' já existe
            pr_exist = Pronunciation.objects.filter(
                keyword=pr_text,
                audio_url=pr_link).first()

            if pr_exist:
                # Se a pronúncia já existir, associamos ao deck
                verify = DeckFlashcardPronunciation.objects.filter(
                    pronunciation_id=pr_exist.id,
                    deck_flashcard_id=deck_flashcard.id)
                if not verify.exists():
                    # Adiciona a pronúncia existente
                    existing_pr_ids.add(pr_exist.id)
                    pr_exist_ids.add(pr_exist.id)
            else:
                # Se a pronúncia não existir, precisamos fazer o upload do áudio para o Firebase
                try:
                    # Realiza o upload do áudio no Firebase
                    firebase_audio_url = upload_audio_from_url_to_firebase(
                        pr_link, pr_text, country, sex, voice_name)
                    # Agora criamos a pronúncia com o novo áudio no Firebase
                    new_pr = Pronunciation(
                        keyword=pr_text,
                        audio_url=firebase_audio_url,
                    )
                    new_pr.save()

                    created_pr = Pronunciation.objects.filter(
                        keyword=pr_text,
                        audio_url=firebase_audio_url).first()

                    existing_pr_ids.add(created_pr.id)
                    pr_exist_ids.add(created_pr.id)

                    # Adiciona à lista de novas pronúncias
                    new_prs.append(new_pr)

                except Exception as e:
                    # Caso ocorra um erro ao fazer o upload ou salvar, retorna a exceção
                    raise ValidationError(
                        f"Erro ao salvar pronúncia: {str(e)}")

    return existing_pr_ids, new_prs, pr_exist_ids


def link_examples_to_deck_flashcard(existing_example_ids, deck_flashcard):
    for example_id in existing_example_ids:
        example = Example.objects.get(id=example_id)
        DeckFlashcardExample.objects.create(
            deck_flashcard=deck_flashcard,
            example=example,
        )


def link_tr_to_deck_flashcard(existing_tr, deck_flashcard):
    for tr_id in existing_tr:
        tr = Translation.objects.get(id=tr_id)
        DeckFlashcardTranslation.objects.create(
            deck_flashcard=deck_flashcard,
            translation=tr,
        )


def link_pr_to_deck_flashcard(existing_pr_ids, deck_flashcard):
    for pr_id in existing_pr_ids:
        pr = Pronunciation.objects.get(id=pr_id)

        # Verifica se a relação já existe, caso contrário cria
        exist = DeckFlashcardPronunciation.objects.filter(
            deck_flashcard=deck_flashcard,
            pronunciation_id=pr_id).exists()
        if not exist:
            DeckFlashcardPronunciation.objects.create(
                deck_flashcard=deck_flashcard,
                pronunciation=pr)
