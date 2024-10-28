from rest_framework.decorators import api_view
from django.http import JsonResponse
from rest_framework import exceptions
from ..serializers_flashcard import FlashCardGetSerializer
from ..serializers_flashcard import UserFlashCardGetSerializer
from rest_framework import status
from django.views.decorators.csrf import csrf_exempt
from ..models import Deck, DeckFlashCard, UserFlashCard
from ..models import FlashCard
from django.core.paginator import Paginator
from django.db.models import Max
from ..validation.validation_jwt import validate_jwt
from ..validation.validation_session import validate_session


@csrf_exempt
@api_view(['GET'])
def get_all_flashcard(request, page_number):
    if request.method == 'GET':
        deck_id = request.data.get('deckId')
        try:
            validate_session()

            token = request.COOKIES.get('jwt_token')
            if not token:
                return JsonResponse({
                    'success': False,
                    'message':
                    'Token de autorização ausente. Faça login novamente.'
                }, status=status.HTTP_401_UNAUTHORIZED)

            jwt_data = validate_jwt(token)
            user_id = jwt_data.get('id')

            if not user_id:
                return JsonResponse({'success': False,
                                    'message': 'userId é necessário'},
                                    status=status.HTTP_400_BAD_REQUEST)

            order_by = request.GET.get('order_by', None)
            new = request.GET.get('New', None)
            learning = request.GET.get('Learning', None)
            reviewing = request.GET.get('Reviewing', None)

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
            flashcards = flashcards.filter(id__in=user_flashcards_qs.values_list('deck_flashcard__flashcard_id', flat=True))

            if order_by == 'newest':
                flashcards = flashcards.order_by('-created_at')
            elif order_by == 'oldest':
                flashcards = flashcards.order_by('created_at')
            elif order_by == 'recently-modified':
                flashcards = flashcards.order_by('-updated_at')
            elif order_by == 'last-time':
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
                                     'Não foi possível encontrar flashcards.'},
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
                                 'message': 'Usuarios não encontrados'},
                                status=status.HTTP_400_BAD_REQUEST)
