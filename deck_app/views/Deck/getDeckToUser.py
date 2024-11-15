from rest_framework.decorators import api_view
from django.http import JsonResponse
from ...serializers_deck import PersonDeckGetSerializer
from rest_framework import status
from django.views.decorators.csrf import csrf_exempt
from ...models import Deck
from ...validation.validation_jwt import validate_jwt


@csrf_exempt
@api_view(['GET'])
def get_all_decks_to_user(request):
    if request.method == 'GET':
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
            if not user_id:
                return JsonResponse({
                    "success": False,
                    "error": ["Token inválido"]
                }, status=status.HTTP_401_UNAUTHORIZED)

            # Buscar todos os decks relacionados ao usuário
            decks = Deck.objects.filter(user_id=user_id)

            # Se não encontrar nenhum deck
            if not decks.exists():
                return JsonResponse({
                    "success": False,
                    "error": ["Nenhum deck encontrado para este usuário."]
                }, status=status.HTTP_404_NOT_FOUND)

            # Serializa os decks encontrados
            serializer = PersonDeckGetSerializer(decks, many=True)

            # Retorna a lista de decks
            return JsonResponse({
                "success": True,
                "decks": serializer.data
            }, status=status.HTTP_200_OK)

        except Exception as e:
            return JsonResponse({
                "success": False,
                "error": str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
