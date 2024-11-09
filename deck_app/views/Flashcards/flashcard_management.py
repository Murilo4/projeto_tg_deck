from rest_framework.decorators import api_view
from django.http import JsonResponse
from rest_framework import exceptions
from ...serializers_flashcard import FlashCardGetSerializer
from ...serializers_flashcard import UserFlashCardGetSerializer
from ...serializers_flashcard import FlashCardGetOneSerializer
from rest_framework import status
from django.views.decorators.csrf import csrf_exempt
from ...models import Deck, DeckFlashCard, UserFlashCard
from ...models import FlashCard, DeckFlashcardExample
from ...models import DeckFlashcardTranslation, DeckFlashcardPronunciation
from ...models import Example, Translation, Pronunciation, FlashcardPhoto
from ...models import FlashCardPriority
from django.db.models import F
from django.core.paginator import Paginator
from django.db.models import Max
from ...validation.validation_jwt import validate_jwt
from ...validation.validation_session import validate_session
from django.db import transaction
import re


@csrf_exempt
@api_view(['GET'])
def get_all_flashcard(request, page_number, deckId):
    if request.method == 'GET':
        deck_id = deckId
        try:
            validate_session()

            token = request.data.get('jwt_token')
            if not token:
                return JsonResponse({
                    'success': False,
                    'message':
                    ['Token de autorização ausente. Faça login novamente.']
                }, status=status.HTTP_401_UNAUTHORIZED)

            jwt_data = validate_jwt(token)
            user_id = jwt_data.get('id')

            if not user_id:
                return JsonResponse({'success': False,
                                    'message': ['userId é necessário']},
                                    status=status.HTTP_400_BAD_REQUEST)

            order_by = request.GET.get('orderBy', None)
            new = request.GET.get('New', None)
            learning = request.GET.get('Learning', None)
            reviewing = request.GET.get('Reviewing', None)
            most_reviewed = request.GET.get('MostReviewed', None)
            least_reviewed = request.GET.get('LeastReviewed', None)

            # Busca UserStandardDeck para o usuário
            deck_flashcard_ids = DeckFlashCard.objects.filter(
                deck_id=deck_id).values_list('flashcard_id', flat=True)

            flashcards = FlashCard.objects.filter(id__in=deck_flashcard_ids)

            user_flashcards_qs = UserFlashCard.objects.filter(
                user_id=user_id, deck_flashcard__deck_id=deck_id)

            if new == 'true':
                user_flashcards_qs = user_flashcards_qs.filter(
                    situation='New')
            if learning == 'true':
                user_flashcards_qs = user_flashcards_qs.filter(
                    situation='Learning')
            if reviewing == 'true':
                user_flashcards_qs = user_flashcards_qs.filter(
                    situation='Reviewing')

            # Filtra os FlashCards que têm UserFlashCards correspondentes
            flashcards = flashcards.filter(
                id__in=user_flashcards_qs.values_list(
                    'deck_flashcard__flashcard_id', flat=True))

            if most_reviewed == 'true':
                flashcards = flashcards.annotate(
                    total_reviews=F('userflashcard__one_star') +
                    F('userflashcard__two_stars') +
                    F('userflashcard__three_stars') +
                    F('userflashcard__four_stars') +
                    F('userflashcard__five_stars')
                ).order_by('-total_reviews')
            elif least_reviewed == 'true':
                flashcards = flashcards.annotate(
                    total_reviews=F('userflashcard__one_star') +
                    F('userflashcard__two_stars') +
                    F('userflashcard__three_stars') +
                    F('userflashcard__four_stars') +
                    F('userflashcard__five_stars')
                ).order_by('total_reviews')

            if order_by == 'newest':
                flashcards = flashcards.order_by('-created_at')
            elif order_by == 'oldest':
                flashcards = flashcards.order_by('created_at')
            elif order_by == 'recentlyModified':
                flashcards = flashcards.order_by('-updated_at')
            elif order_by == 'lastTime':
                user_flashcards = UserFlashCard.objects.filter(
                    user_id=user_id).values(
                        'deck_flashcard__deck_id').annotate(
                            last_time=Max('last_time'))
                recent_deck_ids = [
                    uf['deck_flashcard__deck_id'] for uf in user_flashcards]
                flashcards = flashcards.filter(id__in=recent_deck_ids)

            paginator = Paginator(flashcards, 10)
            page_obj = paginator.get_page(page_number)

            # Formatação da resposta
            response_data = []
            for flashcard in page_obj:

                serializer = FlashCardGetSerializer(flashcard)
                serialized_flashcard = serializer.data
                user_flashcard = None

                # Buscando dados do UserDeck para o deck atual
                deck_flashcard = DeckFlashCard.objects.filter(
                    deck_id=deck_id, flashcard_id=flashcard.id).first()
                user_flashcard = UserFlashCard.objects.filter(
                    deck_flashcard_id=deck_flashcard.id, user_id=user_id
                ).first() if deck_flashcard else None
                user_flashcard_serializer = UserFlashCardGetSerializer(
                    user_flashcard)

                serialized_user_flashcard = user_flashcard_serializer.data if user_flashcard else None

                response_data.append({
                    **serialized_flashcard,
                    **serialized_user_flashcard,
                    'situation':
                    user_flashcard.situation if user_flashcard else None,
                })
            deck_name = Deck.objects.filter(id=deck_id).first()
            if response_data == []:
                return JsonResponse({"success": False,
                                    'message':
                                     ['Não foi possível encontrar flashcards.']},
                                    status=status.HTTP_404_NOT_FOUND)

            return JsonResponse({
                'success': True,
                'message': 'dados retornados',
                'deck':  deck_name.title,
                'flashcard': response_data,
                'hasNext': page_obj.has_next(),
                'hasPrevious': page_obj.has_previous(),
                'pageNumber': page_number,
                'totalPages': paginator.num_pages,
            })
        except exceptions.NotFound:
            return JsonResponse({'success': False,
                                 'message': ['Usuarios não encontrados']},
                                status=status.HTTP_400_BAD_REQUEST)
    else:
        return JsonResponse({"success": False,
                             "message": ["Metodo não autorizado"]},
                            status=status.HTTP_405_METHOD_NOT_ALLOWED)


@csrf_exempt
@api_view(['PUT'])
def update_flashcard(request, flashcardId, deckId):
    if request.method == "PUT":
        try:
            token = request.data.get('jwt_token')
            if not token:
                return JsonResponse({
                    'success': False,
                    'message':
                    ['Token de autorização ausente. Faça login novamente.']
                }, status=status.HTTP_401_UNAUTHORIZED)

            jwt_data = validate_jwt(token)
            user_id = jwt_data.get('id')

            deck = Deck.objects.get(id=deckId)
            if deck.type_deck == "Standard":
                return JsonResponse({
                    "success": False,
                    "message":
                    ["Você não tem permissão para alterar este flashcard"]
                }, status=status.HTTP_403_FORBIDDEN)

            deck_flashcard = DeckFlashCard.objects.get(
                flashcard_id=flashcardId, deck_id=deckId)
            flashcard = FlashCard.objects.get(id=flashcardId)

            with transaction.atomic():
                word_wrong = update_flashcard_data(flashcard, request.data)
                if word_wrong is False:
                    return JsonResponse({'success': False,
                                         'message':
                                        ['Palavra não encontrada na frase']},
                                        status=status.HTTP_400_BAD_REQUEST)

                handle_user_flashcards(deck_flashcard, flashcard, user_id)

                existing_examples, new_examples, exist_example = process_ex(
                    request.data.get('flashcard', {}).get(
                        'examples', []), deck_flashcard)

                existing_pr, new_prs, exist_pr = process_pr(
                    request.data.get('flashcard', {}).get(
                        'pronunciations', []), deck_flashcard)

                existing_tr, new_trs, tr_exist_ids = process_tr(
                    request.data.get('flashcard', {}).get(
                        'translations', []), deck_flashcard)

                img_ids_to_keep, img_ids_to_add = process_img(
                    request.data.get('flashcard', {}).get(
                        'images', []), deck_flashcard)

                if img_ids_to_keep or img_ids_to_add is None:
                    img_ids_to_keep, img_ids_to_add = [], []

                if new_examples:
                    Example.objects.bulk_create(new_examples)

                    for new_example in new_examples:
                        existing_example = Example.objects.filter(
                            text_example=new_example.text_example).first()
                        if existing_example:
                            existing_examples.add(existing_example.id)
                            exist_example.add(existing_example.id)

                if new_prs:
                    Pronunciation.objects.bulk_create(new_prs)
                    for new_pr in new_prs:
                        existing_prs = Pronunciation.objects.filter(
                            keyword=new_pr.keyword,
                            audio_url=new_pr.audio_url).first()
                        if existing_prs:
                            existing_pr.add(existing_prs.id)
                            exist_pr.add(existing_prs.id)

                if new_trs:
                    Translation.objects.bulk_create(new_trs)
                    for new_tr in new_trs:
                        existing_trs = Translation.objects.filter(
                            text_translation=new_tr.text_translation
                        ).first()
                    if existing_trs:
                        existing_tr.add(existing_trs.id)
                        tr_exist_ids.add(existing_trs.id)
                if img_ids_to_add:
                    FlashcardPhoto.objects.bulk_create(img_ids_to_add)
                    for image in img_ids_to_add:
                        existing_img = FlashcardPhoto.objects.filter(
                            file_url=image.file_url).first()
                        if existing_img:
                            img_ids_to_keep.add(existing_img.file_url)

                if existing_examples:
                    link_examples_to_deck_flashcard(
                        existing_examples, deck_flashcard)

                if existing_pr:
                    link_pr_to_deck_flashcard(
                        existing_pr, deck_flashcard)

                if existing_tr:
                    link_tr_to_deck_flashcard(
                        existing_tr, deck_flashcard)

                remove_old_examples(deck_flashcard, exist_example)
                remove_old_pr(deck_flashcard, exist_pr)
                remove_old_tr(deck_flashcard, tr_exist_ids)
                remove_old_img(deck_flashcard, img_ids_to_keep)

            return JsonResponse({
                "success": True,
                "message": ["Flashcard atualizado com sucesso."]
            }, status=status.HTTP_200_OK)

        except DeckFlashCard.DoesNotExist:
            return JsonResponse({'success': False,
                                 'message': ['DeckFlashCard não encontrado.']},
                                status=status.HTTP_404_NOT_FOUND)
        except FlashCard.DoesNotExist:
            return JsonResponse({'success': False,
                                 'message': ['FlashCard não encontrado.']},
                                status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return JsonResponse({'success': False,
                                 'message': f'Erro: {str(e)}'},
                                status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    else:
        return JsonResponse({"success": False,
                             "message": ["Metodo não autorizado"]},
                            status=status.HTTP_405_METHOD_NOT_ALLOWED)


def remove_old_examples(deck_flashcard, exist_ids):
    current_example_ids = DeckFlashcardExample.objects.filter(
        deck_flashcard=deck_flashcard).values_list('example_id', flat=True)

    examples_to_remove = set(current_example_ids) - exist_ids

    DeckFlashcardExample.objects.filter(
        example_id__in=examples_to_remove,
        deck_flashcard=deck_flashcard).delete()


def remove_old_pr(deck_flashcard, exist_pr):
    current_pr_ids = DeckFlashcardPronunciation.objects.filter(
        deck_flashcard=deck_flashcard).values_list(
            'pronunciation_id', flat=True)

    examples_to_remove = set(current_pr_ids) - exist_pr

    DeckFlashcardPronunciation.objects.filter(
        pronunciation_id__in=examples_to_remove,
        deck_flashcard=deck_flashcard).delete()


def remove_old_tr(deck_flashcard, exist_tr_ids):
    current_tr_ids = DeckFlashcardTranslation.objects.filter(
        deck_flashcard=deck_flashcard).values_list(
            'translation_id', flat=True)
    tr_to_remove = set(current_tr_ids) - exist_tr_ids
    DeckFlashcardTranslation.objects.filter(
        translation_id__in=tr_to_remove,
        deck_flashcard=deck_flashcard).delete()


def remove_old_img(deck_flashcard, exist_img_urls):
    current_img_urls = FlashcardPhoto.objects.filter(
        deck_flashcard=deck_flashcard
    ).values_list('file_url', flat=True)

    img_to_remove = set(current_img_urls) - set(exist_img_urls)
    FlashcardPhoto.objects.filter(file_url__in=img_to_remove).delete()


def update_flashcard_data(flashcard, data):
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

        if example_id:
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


def process_img(existing_images, deck_flashcard):
    img_ids_to_keep = set()
    img_ids_to_add = []

    for images_data in existing_images:
        img_id = images_data.get('id')
        img_url = images_data.get('imageUrl')
        img_description = images_data.get('description')
        if img_description is None:
            img_description = ""

        if img_id:
            img = FlashcardPhoto.objects.filter(
                file_url=img_url).first()
            if img:
                img_ids_to_keep.add(img.file_url)
        else:
            img_ids_to_add.append(
                FlashcardPhoto(deck_flashcard_id=deck_flashcard.id,
                               file_url=img_url,
                               file_description=img_description))
    return img_ids_to_keep, img_ids_to_add


def process_tr(tr_data, deck_flashcard):
    existing_tr_ids = set()
    tr_exist_ids = set()
    new_trs = []

    for translation_data in tr_data:
        tr_id = translation_data.get('id')
        tr_text = translation_data.get('textTranslation')

        if tr_id:
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

    for example_data in pr_data:
        pr_id = example_data.get('id')
        pr_text = example_data.get('keyword')
        pr_link = example_data.get('audioUrl')

        if pr_id:
            existing_pr = Pronunciation.objects.filter(id=pr_id).first()
            if existing_pr:
                verify = DeckFlashcardPronunciation.objects.filter(
                    pronunciation_id=existing_pr.id,
                    deck_flashcard_id=deck_flashcard.id)
                if not verify.exists():
                    existing_pr_ids.add(existing_pr.id)
                    pr_exist_ids.add(existing_pr.id)
                if verify.exists():
                    pr_exist_ids.add(existing_pr.id)
        else:
            pr_exist = Pronunciation.objects.filter(
                keyword=pr_text,
                audio_url=pr_link).first()
            if pr_exist:
                verify = DeckFlashcardPronunciation.objects.filter(
                    pronunciation_id=pr_exist.id,
                    deck_flashcard_id=deck_flashcard.id)
                if not verify.exists():
                    existing_pr_ids.add(pr_exist.id)
                    pr_exist_ids.add(pr_exist.id)
                if verify.exists():
                    pr_exist_ids.add(pr_exist.id)
            else:
                new_prs.append(Pronunciation(keyword=pr_text,
                                             audio_url=pr_link))

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
        DeckFlashcardPronunciation.objects.create(
            deck_flashcard=deck_flashcard,
            pronunciation=pr,
        )


@csrf_exempt
@api_view(['GET'])
def get_one_flashcard(request, flashcardId, deckId):
    if request.method == "GET":
        try:
            flashcard = FlashCard.objects.get(id=flashcardId)

            flashcard_serializer = FlashCardGetOneSerializer(flashcard)

            deck_flashcard = DeckFlashCard.objects.get(
                flashcard=flashcard, deck=deckId)

            examples = DeckFlashcardExample.objects.filter(
                deck_flashcard=deck_flashcard).select_related('example')
            example_data = [{'id': ex.example.id,
                             'textExample': ex.example.text_example} for ex in examples] if examples.exists() else []

            pronunciations = DeckFlashcardPronunciation.objects.filter(
                deck_flashcard=deck_flashcard).select_related('pronunciation')
            pronunciation_data = [{'id': pr.pronunciation.id,
                                   'keyword': pr.pronunciation.keyword,
                                   'audioUrl': pr.pronunciation.audio_url} for pr in pronunciations] if pronunciations.exists() else []

            translations = DeckFlashcardTranslation.objects.filter(
                deck_flashcard=deck_flashcard).select_related('translation')
            translations_data = [{'id': tr.translation.id,
                                  'textTranslation': tr.translation.text_translation} for tr in translations] if translations.exists() else []

            response_data = {
                'keyword': flashcard_serializer.data.get('keyword'),
                'mainPhrase': flashcard_serializer.data.get('mainPhrase'),
                'examples': example_data,
                'translations': translations_data,
                'pronunciations': pronunciation_data,
            }

            return JsonResponse({
                'success': True,
                'flashcard': response_data
            }, status=status.HTTP_200_OK)

        except FlashCard.DoesNotExist:
            return JsonResponse({"success": False,
                                 "message": ["FlashCard não encontrado"]},
                                status=status.HTTP_404_NOT_FOUND)
        except DeckFlashCard.DoesNotExist:
            return JsonResponse({"success": False,
                                 "message": ["DeckFlashCard não encontrado"]},
                                status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return JsonResponse({'success': False,
                                 'message': f'Erro: {str(e)}'},
                                status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    else:
        return JsonResponse({"success": False,
                             "message": ["Metodo não autorizado"]},
                            status=status.HTTP_405_METHOD_NOT_ALLOWED)


@csrf_exempt
@api_view(['DELETE'])
def delete_flashcard(request, flashcardId, deckId):
    if request.method == 'DELETE':
        try:
            if not flashcardId:
                return JsonResponse({"success": False,
                                     "message":
                                    ["É necessario informar o flashcard id"]},
                                    status=status.HTTP_400_BAD_REQUEST)

            validate_session()

            token = request.data.get('jwt_token')
            if not token:
                return JsonResponse({
                    'success': False,
                    'message':
                    ['Token de autorização ausente. Faça login novamente.']
                }, status=status.HTTP_401_UNAUTHORIZED)

            jwt_data = validate_jwt(token)
            user_id = jwt_data.get('id')

            if user_id is None:
                return JsonResponse({"success": False,
                                     "message":
                                    ["Usuario não autenticado"]},
                                    status=status.HTTP_403_FORBIDDEN)
            try:
                flashcard = FlashCard.objects.filter(id=flashcardId).first()
                deck_flashcard = DeckFlashCard.objects.filter(
                    deck_id=deckId, flashcard_id=flashcardId).first()
                if not flashcard:
                    return JsonResponse({"success": False,
                                         "message":
                                         ["Nenhum flashcard localizado"]},
                                        status=status.HTTP_403_FORBIDDEN)

                 # Deletar fotos primeiro
                delete_images(deck_flashcard)

                # Deletar traduções
                delete_translation(deck_flashcard)

                # Deletar pronúncias
                delete_pronunciation(deck_flashcard)

                # Deletar exemplos
                delete_examples(deck_flashcard)

                # Deletar user_flashcard
                delete_user_flashcard(deck_flashcard, user_id)

                # Deletar o relacionamento no deck_flashcard
                deck_flashcard.delete()

                # Finalmente, deletar o flashcard
                flashcard.delete()

                return JsonResponse({"success": True,
                                     "message":
                                     ["Flashcard deletado com sucesso"]},
                                    status=status.HTTP_200_OK)
            except exceptions.NotFound:
                return JsonResponse({"success": False,
                                     "message":  ["Flashcard não encontrado"]},
                                    status=status.HTTP_404_NOT_FOUND)
        except exceptions.ValidationError:
            return JsonResponse({"success": False,
                                 "message": ["Flashcard não encontrado"]},
                                status=status.HTTP_404_NOT_FOUND)
    else:
        return JsonResponse({"success": False,
                             "message": ["Metodo não autorizado"]},
                            status=status.HTTP_405_METHOD_NOT_ALLOWED)


def delete_examples(deck_flashcard):
    try:
        examples = DeckFlashcardExample.objects.filter(
            deck_flashcard_id=deck_flashcard.id)
        for example in examples:
            more_one_example = DeckFlashcardExample.objects.filter(
                example_id=example.example_id).count() > 1
            if more_one_example:
                delete_deck_flashcard_example = DeckFlashcardExample.objects.get(
                    example_id=example.example_id)
                delete_deck_flashcard_example.delete()
            else:
                delete_deck_flashcard_example = DeckFlashcardExample.objects.get(
                    example_id=example.example_id)
                delete_example = Example.objects.get(
                    id=example.example_id)
                delete_deck_flashcard_example.delete()
                delete_example.delete()
    except exceptions.NotFound:
        return False
    deleted_examples = True
    return deleted_examples


def delete_translation(deck_flashcard):
    try:
        translations = DeckFlashcardTranslation.objects.filter(
            deck_flashcard_id=deck_flashcard.id)
        for translation in translations:
            more_one_translation = DeckFlashcardTranslation.objects.filter(
                translation_id=translation.translation_id).count() > 1
            if more_one_translation:
                delete_deck_flashcard_tr = DeckFlashcardTranslation.objects.get(
                    translation_id=translation.translation_id,
                    deck_flashcard_id=deck_flashcard.id)
                delete_deck_flashcard_tr.delete()
            else:
                delete_deck_flashcard_tr = DeckFlashcardTranslation.objects.get(
                    translation_id=translation.translation_id,
                    deck_flashcard_id=deck_flashcard.id)
                delete_tr = Translation.objects.get(
                    id=translation.translation_id)
                delete_deck_flashcard_tr.delete()
                delete_tr.delete()
        deleted_translation = True
        return deleted_translation
    except exceptions.NotFound:
        return False


def delete_pronunciation(deck_flashcard):
    try:
        audios = DeckFlashcardPronunciation.objects.filter(
            deck_flashcard_id=deck_flashcard.id
        )
        for audio in audios:
            more_one_audio = DeckFlashcardPronunciation.objects.filter(
                pronunciation_id=audio.pronunciation_id).count() > 1
            if more_one_audio:
                delete_deck_pr = DeckFlashcardPronunciation.objects.get(
                    pronunciation_id=audio.id)
                delete_deck_pr.delete()
            else:
                delete_deck_pr = DeckFlashcardPronunciation.objects.get(
                    pronunciation_id=audio.pronunciation_id)
                delete_deck_pr.delete()
                delete_pr = Pronunciation.objects.get(
                    id=audio.pronunciation_id)
                delete_pr.delete()
        deleted_translation = True
        return deleted_translation
    except exceptions.NotFound:
        return False


def delete_images(deck_flashcard):
    try:
        images = FlashcardPhoto.objects.filter(
            deck_flashcard_id=deck_flashcard.id
        )
        for image in images:
            image.delete()
        deleted_images = True
        return deleted_images
    except exceptions.NotFound:
        return False


def delete_user_flashcard(deck_flashcard, user_id):
    try:
        user_flashcard = UserFlashCard.objects.filter(
            deck_flashcard_id=deck_flashcard.id,
            user_id=user_id)
        if user_flashcard:
            user_flashcard.delete()
            deleted_user_flashcard = True
        else:
            deleted_user_flashcard = False

        user_priority = FlashCardPriority.objects.filter(
            deck_flashcard_id=deck_flashcard.id,
            user_id=user_id)
        if user_priority:
            user_priority.delete()
            deleted_user_priority = True
        else:
            deleted_user_priority = False

        return deleted_user_flashcard, deleted_user_priority
    except exceptions.NotFound:
        return False
