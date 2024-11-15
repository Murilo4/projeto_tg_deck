from rest_framework.decorators import api_view
from django.http import JsonResponse
from rest_framework import status
from django.views.decorators.csrf import csrf_exempt
from rest_framework import exceptions
from ...serializers_deck import PersonDeckSerializer, UDPreferencesSerializer
from ...serializers_deck import UserDeckSerializer, CreateStandardDecks
from ...validation.validation_session import validate_session
from ...validation.validation_jwt import validate_jwt


@csrf_exempt
@api_view(['POST'])
def create_deck(request):
    if request.method == 'POST':
        try:

            token = request.headers.get('Authorization')
            if not token:
                return JsonResponse({
                    'success': False,
                    'message':
                    ['Token de autorização ausente. Faça login novamente.']
                }, status=status.HTTP_401_UNAUTHORIZED)

            jwt_data = validate_jwt(token)

            user_id = jwt_data.get('id')
            deck_name = request.data.get('deckName')
            description = request.data.get('description')
            img_url = request.data.get('img')
            color = request.data.get('color')
            type_deck = request.data.get('typedeck')
            difficult = request.data.get('difficult')
            new = request.data.get("new")
            learning = request.data.get('learning')
            review = request.data.get('review')

            if not difficult:
                difficult = None

            if not type_deck:
                type_deck = "Custom"

            if not user_id:
                return JsonResponse({'success': False,
                                    'message': ['Usuario não encontrado']},
                                    status=status.HTTP_400_BAD_REQUEST)

            if not deck_name:
                return JsonResponse({'success': False,
                                    'message': ['Ñome do deck é requerido ']},
                                    status=status.HTTP_400_BAD_REQUEST)
            if not description:
                return JsonResponse({"success": False,
                                     "message":
                                    ["É necessario informar a descrição"]},
                                    status=status.HTTP_400_BAD_REQUEST)

            if not img_url:
                return JsonResponse({'success': False,
                                    'message': ['Image URL é necessario']},
                                    status=status.HTTP_400_BAD_REQUEST)
            if not new:
                new = 2
            if not learning:
                learning = 5
            if not review:
                review = 2

            if type_deck == "Custom":
                new_deck = {
                    'title': deck_name,
                    'description_deck': description,
                    'image': img_url,
                    'color_predefinition': color,
                }
                serializer = PersonDeckSerializer(data=new_deck)
                if serializer.is_valid(raise_exception=True):
                    deck = serializer.save()
                    deck_id = deck.id
                    new_user_deck = {
                        'user_id': user_id,
                        'deck_id': deck_id
                    }
                    serializer_user_deck = UserDeckSerializer(
                        data=new_user_deck)

                    if serializer_user_deck.is_valid(raise_exception=True):
                        serializer_user_deck.save()
                        preferences = {'user_id': user_id,
                                       'deck_id': deck_id,
                                       'new_per_day': new,
                                       'learning_per_day': learning,
                                       'review_per_day': review}
                        user_deck_preferences = UDPreferencesSerializer(
                            data=preferences)
                        if user_deck_preferences.is_valid(
                                raise_exception=True):
                            user_deck_preferences.save()
                            return JsonResponse({'success': True,
                                                'message':
                                                 ['Deck criado com sucesso']},
                                                status=status.HTTP_201_CREATED)
                else:
                    return JsonResponse({
                        'success': False,
                        'message':
                        ['Não foi possivel validar os dados']},
                        status=status.HTTP_400_BAD_REQUEST)
            else:
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
                    return JsonResponse({'success': True,
                                        'message':
                                         ['Deck criado com sucesso']},
                                        status=status.HTTP_201_CREATED)
        except exceptions.NotFound:
            return JsonResponse({'success': False,
                                 'message':
                                ['não foi possivel validar os dados']},
                                status=status.HTTP_404_NOT_FOUND)
    else:
        return JsonResponse({'success': False,
                            'message':  ['Método não suportado']},
                            status=status.HTTP_405_METHOD_NOT_ALLOWED)
