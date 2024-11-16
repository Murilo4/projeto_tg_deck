from rest_framework.decorators import api_view
from django.http import JsonResponse
from rest_framework import status
from django.views.decorators.csrf import csrf_exempt
from ...models import Deck, UserDeck, DeckFlashCard, UserFlashCard
from ...models import UserDeckPreferences
from django.db.models import Q
from ...validation.validation_jwt import validate_jwt


@csrf_exempt
@api_view(['POST'])
def add_deck_to_user(request, deckId):
    if request.method == 'POST':
        deck_id = deckId
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

            if not deck_id:
                return JsonResponse({'success': False,
                                    'error': ['Deck não encontrado.']},
                                    status=status.HTTP_404_NOT_FOUND)

            if UserDeck.objects.filter(
                    user_id=user_id, deck_id=deck_id).exists():

                return JsonResponse({"success": False,
                                    "error": ["Deck já pertence ao usuário."]},
                                    status=status.HTTP_409_CONFLICT)
            deck = Deck.objects.get(id=deck_id)
            if deck.public == 0:
                return JsonResponse({"success": False,
                                     "error": ["Deck não é público."]},
                                    status=status.HTTP_403_FORBIDDEN)

            standard_deck = Deck.objects.get(Q(id=deck_id) & (
                Q(type_deck="Standard") | Q(type_deck="Custom")) & Q(public=1))

            user_standard_deck = UserDeck.objects.create(
                user_id=user_id, deck_id=standard_deck.id)

            user_deck_preferences = UserDeckPreferences.objects.create(
                user_id=user_id, deck_id=standard_deck.id,
                new_per_day=3, learning_per_day=15,
                review_per_day=2
            )
            if user_deck_preferences is None:
                return JsonResponse({
                    "success": False,
                    "error": ["Erro ao adicionar deck"]},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR)

            if user_standard_deck is None:
                return JsonResponse({
                    "success": False,
                    "error": ["Erro ao adicionar deck"]},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR)

            # Adicionando flashcards do deck para o usuário
            deck_flashcards = DeckFlashCard.objects.filter(deck_id=deck_id)
            for deck_flashcard in deck_flashcards:
                UserFlashCard.objects.create(
                    user_id=user_id,
                    deck_flashcard_id=deck_flashcard.id,
                    situation="new"
                )

            return JsonResponse({'success': True,
                                'message': ['Deck adicionados com sucesso']},
                                status=status.HTTP_201_CREATED)

        except Deck.DoesNotExist:
            return JsonResponse({'success': False,
                                'error': ['Deck não encontrado.']},
                                status=status.HTTP_404_NOT_FOUND)
    else:
        return JsonResponse({"success": False,
                             "error": ["Metodo não autorizado"]},
                            status=status.HTTP_405_METHOD_NOT_ALLOWED)


@csrf_exempt
@api_view(['GET'])
def cron_job(request):
    return JsonResponse({'message': ['Cron job executed successfully']},
                        status=status.HTTP_200_OK)
