from rest_framework.decorators import api_view
from django.http import JsonResponse
from rest_framework import exceptions
from rest_framework import status
from django.views.decorators.csrf import csrf_exempt
from ...models import Deck, UserDeck, DeckFlashCard
from ...validation.validation_jwt import validate_jwt
from django.db.models import Count


@csrf_exempt
@api_view(["GET"])
def get_min_max_flashcard(request):
    if request.method == 'GET':
        try:
            token = request.headers.get('Authorization')
            if not token:
                return JsonResponse({
                    'success': False,
                    'error':
                    ['Token de autorização ausente.']
                }, status=status.HTTP_401_UNAUTHORIZED)

            jwt_data = validate_jwt(token)
            user_id = jwt_data.get('id')
            if not user_id:
                return JsonResponse({
                    "success": False,
                    "error": ["Token inválido"]
                }, status=status.HTTP_401_UNAUTHORIZED)

            user_decks = UserDeck.objects.filter(user_id=user_id).values_list(
                'deck_id', flat=True)
            deck_ids = list(user_decks)

            decks = Deck.objects.filter(id__in=deck_ids)

            flashcard_counts = DeckFlashCard.objects.values(
                'deck_id').annotate(flashcard_count=Count('flashcard_id'))

            # Dicionário para contar flashcards de cada deck
            flashcard_counts_dict = {
                entry['deck_id']: entry['flashcard_count'] for entry in flashcard_counts}

            flashcard_counts_list = []

            for deck in decks:
                flashcard_count = flashcard_counts_dict.get(deck.id, 0)
                flashcard_counts_list.append(flashcard_count)

            flashcard_min = min(
                flashcard_counts_list) if flashcard_counts_list else 0
            flashcard_max = max(
                flashcard_counts_list) if flashcard_counts_list else 0

            return JsonResponse({"success": True,
                                 "message": "valores retornados",
                                "flashcardMin": flashcard_min,
                                 "flashcardMax": flashcard_max},
                                status=status.HTTP_200_OK)
        except exceptions.NotFound:
            return JsonResponse({"success": False,
                                 "error": "deck não encontrado"},
                                status=status.HTTP_400_BAD_REQUEST)

    else:
        return JsonResponse({"success": False,
                            "error": ["Metodo não autorizado"]},
                            status=status.HTTP_405_METHOD_NOT_ALLOWED)
