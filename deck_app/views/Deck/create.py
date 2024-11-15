from rest_framework.decorators import api_view
from django.http import JsonResponse
from rest_framework import status
from django.views.decorators.csrf import csrf_exempt
from rest_framework import exceptions
from ...serializers_deck import PersonDeckCreateSerializer, UDPreferencesSerializer
from ...serializers_deck import UserDeckSerializer, CreateStandardDecks
from django.db import transaction
from ...validation.validation_jwt import validate_jwt


@csrf_exempt
@api_view(['POST'])
def create_deck(request):
    if request.method == 'POST':
        try:
            # Recuperando o token de autorização
            token = request.headers.get('Authorization')
            if not token:
                return JsonResponse({
                    'success': False,
                    'message': ['Token de autorização ausente. Faça login novamente.']
                }, status=status.HTTP_401_UNAUTHORIZED)

            # Validando o token
            jwt_data = validate_jwt(token)
            user_id = jwt_data.get('id')

            # Obtendo os dados da requisição
            deck_name = request.data.get('deckName')
            description = request.data.get('description')
            img_url = request.data.get('img')
            color = request.data.get('color')
            type_deck = request.data.get('typedeck')
            difficult = request.data.get('difficult')
            new = request.data.get("new")
            learning = request.data.get('learning')
            review = request.data.get('review')

            # Definindo valores padrão
            if not difficult:
                difficult = None
            if not type_deck:
                type_deck = "Custom"
            if not user_id:
                return JsonResponse({'success': False, 'message': ['Usuario não encontrado']}, status=status.HTTP_400_BAD_REQUEST)
            if not deck_name:
                return JsonResponse({'success': False, 'message': ['Nome do deck é requerido']}, status=status.HTTP_400_BAD_REQUEST)
            if not description:
                return JsonResponse({"success": False, "message": ["É necessário informar a descrição"]}, status=status.HTTP_400_BAD_REQUEST)
            if not img_url:
                return JsonResponse({'success': False, 'message': ['Image URL é necessário']}, status=status.HTTP_400_BAD_REQUEST)
            if not new:
                new = 2
            if not learning:
                learning = 5
            if not review:
                review = 2

            # Iniciando a transação atômica
            with transaction.atomic():
                if type_deck == "Custom":
                    # Preparando os dados para o deck customizado
                    new_deck = {
                        'title': deck_name,
                        'description_deck': description,
                        'image': img_url,
                        'color': color,
                        'type': type_deck,
                        'reviews': 0,
                        'public': 0,
                        'allow_copy': 0,
                        'stars': 0
                    }
                    # Criando o deck
                    serializer = PersonDeckCreateSerializer(data=new_deck)
                    if serializer.is_valid(raise_exception=True):
                        deck = serializer.save()
                        deck_id = deck.id

                        # Criando o relacionamento UserDeck
                        new_user_deck = {'user_id': user_id, 'deck_id': deck_id}
                        serializer_user_deck = UserDeckSerializer(data=new_user_deck)
                        if serializer_user_deck.is_valid(raise_exception=True):
                            serializer_user_deck.save()

                            # Criando as preferências do usuário
                            preferences = {
                                'user_id': user_id,
                                'deck_id': deck_id,
                                'new_per_day': new,
                                'learning_per_day': learning,
                                'review_per_day': review
                            }
                            user_deck_preferences = UDPreferencesSerializer(data=preferences)
                            if user_deck_preferences.is_valid(raise_exception=True):
                                user_deck_preferences.save()

                                # Se tudo for bem-sucedido, comita as transações
                                return JsonResponse({
                                    'success': True,
                                    'message': ['Deck criado com sucesso']
                                }, status=status.HTTP_201_CREATED)
                else:
                    # Criando um deck do tipo padrão
                    new_deck_default = {
                        'title': deck_name,
                        'description_deck': description,
                        'image': img_url,
                        'color_predefinition': color,
                        'difficult': difficult,
                        "type_deck": "Standard",
                        'public': True
                    }
                    serializer = CreateStandardDecks(data=new_deck_default)
                    if serializer.is_valid(raise_exception=True):
                        serializer.save()

                        # Se o deck padrão for salvo com sucesso
                        return JsonResponse({
                            'success': True,
                            'message': ['Deck criado com sucesso']
                        }, status=status.HTTP_201_CREATED)

        except NotFound:
            return JsonResponse({'success': False, 'message': ['Não foi possível validar os dados']}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            # Qualquer outro erro será capturado e uma resposta de erro será retornada
            return JsonResponse({'success': False, 'message': [f'Erro inesperado: {str(e)}']}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    else:
        return JsonResponse({'success': False, 'message': ['Método não suportado']}, status=status.HTTP_405_METHOD_NOT_ALLOWED)