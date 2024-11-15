from rest_framework.decorators import api_view
from django.http import JsonResponse
from rest_framework import exceptions
from rest_framework import status
from django.views.decorators.csrf import csrf_exempt
from ...models import Deck, UserDeck, DeckFlashCard, UserFlashCard
from ...validation.validation_jwt import validate_jwt
from ..Flashcards.flashcard_management import delete_flashcard


@csrf_exempt
@api_view(['DELETE'])
def delete_deck(request, deckId):
    if request.method == 'DELETE':
        try:
            deck_id = deckId

            token = request.headers.get('Authorization')
            if not token:
                return JsonResponse({
                    'success': False,
                    'error': ['Token de autorização ausente.']
                }, status=status.HTTP_401_UNAUTHORIZED)

            # Função de validação do JWT
            jwt_data = validate_jwt(token)
            user_id = jwt_data.get('id')

            if not user_id:
                return JsonResponse({'success': False,
                                     'error': ['userId é necessário']},
                                    status=status.HTTP_400_BAD_REQUEST)

            deck_user = UserDeck.objects.filter(
                deck_id=deck_id, user_id=user_id)
            if not deck_user:
                return JsonResponse({
                    'success': False,
                    'error':
                    ['Deck não encontrado para este usuário']},
                    status=status.HTTP_404_NOT_FOUND)

            deck = Deck.objects.filter(id=deck_id).first()
            if not deck:
                return JsonResponse({
                    'success': False,
                    'error':
                    ['Deck não encontrado para este usuário']},
                    status=status.HTTP_404_NOT_FOUND)

            deck_flashcards = DeckFlashCard.objects.filter(deck_id=deck_id)

            if deck.type_deck == 'Custom' and deck.public == 0:
                for deck_flashcard in deck_flashcards:
                    flashcard_id = deck_flashcard.flashcard_id

                    delete_flashcard(request, flashcard_id, deck_id)
                deck_user.delete()
                deck.delete()

            elif deck.type_deck == 'Custom' and deck.public == 1:
                user_deck = UserDeck.objects.filter(
                    deck_id=deck_id).count() > 1
                for deck_flashcard in deck_flashcards:
                    flashcard_id = deck_flashcard.flashcard_id

                    delete_flashcard(request, flashcard_id, deck_id)
                if user_deck:
                    deck_user.delete()
            elif deck.type_deck == 'Standard':
                deck_user.delete()
                for deck_flashcard in deck_flashcards:
                    user_flashcard = UserFlashCard.objects.filter(
                        user_id=user_id,
                        deck_flashcard_id=deck_flashcard.id
                    )
                    user_flashcard.delete()

            return JsonResponse({
                'success': True,
                'message': ['Deck removido com sucesso.'],
            })
        except exceptions.NotFound:
            return JsonResponse({'success': False,
                                 'error': ['Usuário não encontrado']},
                                status=status.HTTP_400_BAD_REQUEST)
    else:
        return JsonResponse({"success": False,
                             "error": ["Método não autorizado"]},
                            status=status.HTTP_405_METHOD_NOT_ALLOWED)
