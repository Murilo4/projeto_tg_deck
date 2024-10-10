from rest_framework.decorators import api_view
from django.http import JsonResponse
from rest_framework import status
from django.views.decorators.csrf import csrf_exempt
from rest_framework import exceptions
from ..serializers import DeckSerializer


@csrf_exempt
@api_view(['POST'])
def create_deck(request):
    if request.method == 'POST':
        try:
            user_id = request.data.get('userId')
            deck_name = request.data.get('deckName')
            description = request.data.get('description')
            img_url = request.data.get('img')
            # color = request.data.get('color')

            if not user_id:
                return JsonResponse({'success': False,
                                    'message': 'Usuario não encontrado'},
                                    status=status.HTTP_400_BAD_REQUEST)

            if not deck_name:
                return JsonResponse({'success': False,
                                    'message': 'Deck name is required'},
                                    status=status.HTTP_400_BAD_REQUEST)
            if not description:
                description = ' '
            if not img_url:
                return JsonResponse({'success': False,
                                    'message': 'Image URL is required'},
                                    status=status.HTTP_400_BAD_REQUEST
                                    )

            new_deck = {
                'user_id': user_id,
                'deck_name': deck_name,
                'description': description,
                'img_url': img_url
                # 'color': color
            }

            serializer = DeckSerializer(data=new_deck)
            if serializer.is_valid(raise_exception=True):
                serializer.save()
                return JsonResponse({'success': True,
                                    'message': 'Deck criado com sucesso'},
                                    status=status.HTTP_201_CREATED)
            else:
                return JsonResponse({'success': False,
                                    'message':
                                     'Não foi possivel validar os dados'},
                                    status=status.HTTP_400_BAD_REQUEST)
        except exceptions.NotFound:
            return JsonResponse({'success': False,
                                 'message':
                                'não foi possivel validar os dados inseridos'},
                                status=status.HTTP_404_NOT_FOUND)

    else:
        return JsonResponse({'success': False,
                            'message':  'Método não suportado'},
                            status=status.HTTP_405_METHOD_NOT_ALLOWED)
