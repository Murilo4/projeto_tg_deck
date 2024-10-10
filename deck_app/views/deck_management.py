from rest_framework.decorators import api_view
from django.http import JsonResponse
from rest_framework import exceptions
from ..serializers import DeckGetSerializer, DeckSerializer, DeckUpdateSerializer
from rest_framework import status
from django.views.decorators.csrf import csrf_exempt
from ..models import Deck


@csrf_exempt
@api_view(['GET'])
def get_all_decks(request):
    if request.method == 'GET':
        try:
            user_id = request.data.get('userId')  # Mude para request.GET
            if not user_id:
                return JsonResponse({'success': False,
                                     'message': 'userId é necessário'},
                                    status=status.HTTP_400_BAD_REQUEST)

            decks = Deck.objects.filter(user_id=user_id)

            serializer = DeckGetSerializer(decks, many=True)

            return JsonResponse({
                'success': True,
                'message': 'dados retornados',
                'data': serializer
            })
        except exceptions.NotFound:
            return JsonResponse({'success': False,
                                 'message': ''},
                                status=status.HTTP_400_BAD_REQUEST)


@csrf_exempt
@api_view(['PUT'])
def deck_update(request):
    if request.method == 'PUT':
        try:
            user_id = request.data.get('userId')

            deck = Deck.objects.filter(user_id=user_id)

            serializer = DeckUpdateSerializer(deck, data=request.data,
                                              partial=True)

            if serializer.is_valid():
                updated_serializer = serializer.validated_data
                deck_name = updated_serializer.get('deck_name')
                deck_description = updated_serializer.get('deck_description')
                deck_image = updated_serializer.get('deck_image')

                deck_updated = {
                    'deckName': deck_name,
                    'deckDescription': deck_description,
                    'deckImage': deck_image
                }

                serializer.save()
                return JsonResponse({
                    'success': True,
                    'message': 'deck atualizado',
                    'data': deck_updated
                })
            else:
                return JsonResponse({'success': False,
                                     'message':
                                     'Não foi possivel validar os dados do deck'},
                                    status=status.HTTP_400_BAD_REQUEST)
        except exceptions.NotFound:
            return JsonResponse({'success': False,
                                'message': ''},
                                status=status.HTTP_400_BAD_REQUEST)


@csrf_exempt
@api_view(['DELETE'])
def deck_delete(request):
    if request.method == 'DELETE':
        try:
            # Recuperar o usuário e o deck
            user = User.objects.get(id=user_id)
            deck = Deck.objects.get(id=deck_id)

            # Verificar se o deck é predefinido
            if not deck.is_predefined:
                deck.delete()
                return JsonResponse({'error': 'Deck não é predefinido'}, status=400)

            # Remover a relação do usuário com o deck
            user.decks.remove(deck)

            return JsonResponse({'message': 'Relação removida com sucesso'}, status=200)

        except User.DoesNotExist:
            return JsonResponse({'error': 'Usuário não encontrado'}, status=404)
        except Deck.DoesNotExist:
            return JsonResponse({'error': 'Deck não encontrado'}, status=404)
