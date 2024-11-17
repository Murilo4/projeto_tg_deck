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
from django.core.cache import cache


@csrf_exempt
@api_view(['PUT'])
def update_flashcard(request, flashcardId, deckId):
    if request.method == "PUT":
        try:
            token = request.headers.get('Authorization')
            if not token:
                return JsonResponse({
                    'success': False,
                    'error':
                    ['Token de autorização ausente. Faça login novamente.']
                }, status=status.HTTP_401_UNAUTHORIZED)

            jwt_data = validate_jwt(token)
            user_id = jwt_data.get('id')

            deck = Deck.objects.get(id=deckId)
            if deck.type_deck == "Standard":
                return JsonResponse({
                    "success": False,
                    "error":
                    ["Você não tem permissão para alterar este flashcard"]
                }, status=status.HTTP_403_FORBIDDEN)

            deck_flashcard = DeckFlashCard.objects.get(
                flashcard_id=flashcardId, deck_id=deckId)
            flashcard = FlashCard.objects.get(id=flashcardId)

            with transaction.atomic():
                word_wrong = update_flashcard_data(flashcard, request.data)
                if word_wrong is False:
                    return JsonResponse({'success': False,
                                         'error':
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

                # img_ids_to_keep, img_ids_to_add = process_img(
                #     request.data.get('flashcard', {}).get(
                #         'images', []), deck_flashcard)

                # if img_ids_to_keep or img_ids_to_add is None:
                #     img_ids_to_keep, img_ids_to_add = [], []

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
                # if img_ids_to_add:
                #     FlashcardPhoto.objects.bulk_create(img_ids_to_add)
                #     for image in img_ids_to_add:
                #         existing_img = FlashcardPhoto.objects.filter(
                #             file_url=image.file_url).first()
                #         if existing_img:
                #             img_ids_to_keep.add(existing_img.file_url)

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
                # remove_old_img(deck_flashcard, img_ids_to_keep)

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
                             "error": ["Metodo não autorizado"]},
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
    

# @csrf_exempt
# @api_view(['PUT'])
# def update_flashcard(request, flashcardId, deckId):
#     if request.method == "PUT":
#         try:
#             token = request.headers.get('Authorization')
#             if not token:
#                 return JsonResponse({
#                     'success': False,
#                     'error': ['Token de autorização ausente. Faça login novamente.']
#                 }, status=status.HTTP_401_UNAUTHORIZED)

#             jwt_data = validate_jwt(token)
#             user_id = jwt_data.get('id')

#             deck = Deck.objects.get(id=deckId)
#             if deck.type_deck == "Standard":
#                 return JsonResponse({
#                     "success": False,
#                     "error": ["Você não tem permissão para alterar este flashcard"]
#                 }, status=status.HTTP_403_FORBIDDEN)

#             # Recuperar dados do cache
#             cached_data = cache.get(f"flashcard_{flashcardId}_deck_{deckId}")
#             if not cached_data:
#                 return JsonResponse({
#                     "success": False,
#                     "error": ["Cache expirado ou não encontrado. Refaça a busca."]
#                 }, status=status.HTTP_400_BAD_REQUEST)

#             new_data = request.data.get('flashcard', {})
#             with transaction.atomic():
#                 # Comparar exemplos
#                 existing_examples, new_examples, removed_examples = compare_data(
#                     cached_data["flashcard"]["examples"], new_data.get("examples", [])
#                 )

#                 # Comparar pronúncias
#                 existing_pr, new_prs, removed_prs = compare_data(
#                     cached_data["flashcard"]["pronunciations"], new_data.get("pronunciations", [])
#                 )

#                 # Comparar traduções
#                 existing_tr, new_trs, removed_trs = compare_data(
#                     cached_data["flashcard"]["translations"], new_data.get("translations", [])
#                 )

#                 # Processar adições, modificações e remoções
#                 process_additions(new_examples, Pronunciation, deck_flashcard)
#                 process_removals(removed_examples, Example, deck_flashcard)

#                 # Limpar cache após atualização
#                 cache.delete(f"flashcard_{flashcardId}_deck_{deckId}")

#             return JsonResponse({"success": True, "message": "Flashcard atualizado com sucesso."}, status=200)

#         except Exception as e:
#             return JsonResponse({"success": False, "error": str(e)}, status=500)
#     else:
#         return JsonResponse({"success": False, "error": ["Metodo não autorizado"]}, status=405)


# def compare_data(cached_list, new_list):
#     cached_set = {item['id'] for item in cached_list}
#     new_set = {item.get('id') for item in new_list if 'id' in item}

#     to_remove = cached_set - new_set
#     to_add = [item for item in new_list if item.get('id') not in cached_set]
#     existing = cached_set & new_set

#     return existing, to_add, to_remove


# def process_additions(new_items, model, deck_flashcard):
#     """
#     Adiciona novos itens ao banco de dados e os vincula ao deck_flashcard.
    
#     Args:
#         new_items (list): Lista de novos itens a serem adicionados.
#         model (Django Model): O modelo para os itens (e.g., Example, Pronunciation, Translation).
#         deck_flashcard (DeckFlashCard): O objeto DeckFlashCard associado.
#     """
#     if not new_items:
#         return

#     # Criar novas instâncias do modelo com os dados fornecidos
#     objects_to_create = [
#         model(**item) for item in new_items if isinstance(item, dict)
#     ]
#     model.objects.bulk_create(objects_to_create)

#     created_items = model.objects.filter(**{
#         f"{model._meta.model_name}_id__in": [obj.id for obj in objects_to_create]
#     })

#     relation_model = get_relation_model(model)
#     relation_instances = [
#         relation_model(deck_flashcard=deck_flashcard, **{f"{model._meta.model_name}_id": obj.id})
#         for obj in created_items
#     ]
#     relation_model.objects.bulk_create(relation_instances)


# def get_relation_model(model):
#     relation_mapping = {
#         Example: DeckFlashcardExample,
#         Pronunciation: DeckFlashcardPronunciation,
#         Translation: DeckFlashcardTranslation,
#         # Adicione outros mapeamentos se necessário
#     }
#     return relation_mapping.get(model)


# def process_removals_with_objects(sent_objects, model, deck_flashcard, relation_field, unique_fields):
#     """
#     Remove objetos que não estão nos dados enviados pelo cliente.

#     :param sent_objects: Lista de objetos enviados pelo cliente.
#     :param model: Modelo Django que será filtrado.
#     :param deck_flashcard: Instância de DeckFlashCard associada.
#     :param relation_field: Nome do campo relacionado no modelo.
#     :param unique_fields: Campos únicos usados para identificar os objetos no banco.
#     """
#     # Obter objetos existentes relacionados ao deck_flashcard
#     current_objects = model.objects.filter(
#         **{relation_field: deck_flashcard}
#     ).values(*unique_fields)

#     # Transformar objetos existentes em um conjunto de dicionários
#     current_set = {tuple(obj[field] for field in unique_fields) for obj in current_objects}

#     # Transformar objetos enviados em um conjunto de dicionários
#     sent_set = {tuple(obj[field] for field in unique_fields) for obj in sent_objects}

#     # Identificar objetos a serem removidos
#     to_remove = current_set - sent_set

#     # Remover os objetos que não estão mais na lista enviada
#     if to_remove:
#         model.objects.filter(
#             **{relation_field: deck_flashcard},
#             **{
#                 f"{field}__in": [value[idx] for value in to_remove]
#                 for idx, field in enumerate(unique_fields)
#             }
#         ).delete()
# def process_img(existing_images, deck_flashcard):
#     img_ids_to_keep = set()
#     img_ids_to_add = []

#     for images_data in existing_images:
#         img_url = images_data.get('imageUrl')
#         img_description = images_data.get('description', "")

#         if img_url:
#             img = FlashcardPhoto.objects.filter(file_url=img_url).first()
#             if img:
#                 img_ids_to_keep.add(img.file_url)
#             else:
#                 # If image doesn't exist, add it to the new list
#                 img_ids_to_add.append(FlashcardPhoto(
#                     deck_flashcard_id=deck_flashcard.id,
#                     file_url=img_url,
#                     file_description=img_description
#                 ))
#         else:
#             img = FlashcardPhoto.objects.filter(file_url=img_url).first()
#             if img:
#                 img_ids_to_keep.add(img.file_url)
#             else:
#                 img_ids_to_add.append(FlashcardPhoto(
#                     deck_flashcard_id=deck_flashcard.id,
#                     file_url=img_url,
#                     file_description=img_description
#                 ))

#     # Ensure no duplicates are added
#     FlashcardPhoto.objects.bulk_create(img_ids_to_add)
    
#     return img_ids_to_keep, img_ids_to_add


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