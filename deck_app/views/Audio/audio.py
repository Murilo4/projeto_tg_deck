from rest_framework.decorators import api_view
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
import os
import requests
from rest_framework import status
FORVO_API_KEY = os.getenv("FORVO_KEY")


@csrf_exempt
@api_view(['POST'])
def get_pronunciations(request):
    word = request.data.get("word")

    url = f"https://apifree.forvo.com/action/word-pronunciations/format/json/word/{word}/id_lang_speak/39/key/{FORVO_API_KEY}/"

    try:
        response = requests.get(url)

        if response.status_code == 200:
            data = response.json()

            if data.get('items'):
                audio_info = []

                for item in data['items']:
                    audio_data = {
                        'audioUrl': item.get('pathmp3'),
                        'voiceName': item.get('username'),
                        'sex': item.get('sex'),
                        'country': item.get('country')
                    }
                    audio_info.append(audio_data)

                return JsonResponse({'success': True,
                                     'message': "dados retornados",
                                    'audioInfo': audio_info},
                                    status=status.HTTP_200_OK)
            else:
                return JsonResponse({'success': False,
                                    'error': 'Pronúncia não encontrada.'},
                                    status=status.HTTP_404_NOT_FOUND)
        else:
            return JsonResponse({"success": False,
                                'error': 'Erro na requisição à API do Forvo'},
                                status=response.status_code)

    except requests.exceptions.RequestException:
        return JsonResponse({"success": False,
                            'error': 'Erro de conexão com a API do Forvo'},
                            status=status.HTTP_500_INTERNAL_SERVER_ERROR)
