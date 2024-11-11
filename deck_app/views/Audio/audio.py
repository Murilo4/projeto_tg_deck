from rest_framework.decorators import api_view
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
import os
import requests
FORVO_API_KEY = os.getenv("FORVO_KEY")


@csrf_exempt
@api_view(['POST'])
def get_pronunciations(request):
    word = request.data.get("word")

    url = f"https://apifree.forvo.com/action/word-pronunciations/format/json/word/{word}/id_lang_speak/39/key/{FORVO_API_KEY}/"

    # Realizar a requisição à API
    try:
        # Realizar a requisição à API
        response = requests.get(url)
        
        # Exibir o código de status da resposta e o conteúdo
        print("Status Code:", response.status_code)
        print("Response Body:", response.text)

        if response.status_code == 200:
            data = response.json()

            if data.get('items'):
                # Lista para armazenar as informações de áudio
                audio_info = []
                
                # Iterar sobre todas as opções de áudio disponíveis
                for item in data['items']:
                    audio_data = {
                        'audioUrl': item.get('pathmp3'),
                        'voiceName': item.get('username'),
                        'sex': item.get('sex'),
                        'country': item.get('country')
                    }
                    audio_info.append(audio_data)
                
                # Retornar as informações de áudio
                return JsonResponse({'audio_info': audio_info})
            else:
                return JsonResponse({'error': 'Pronúncia não encontrada.'}, status=404)
        else:
            return JsonResponse({'error': f'Erro na requisição à API do Forvo: {response.status_code} - {response.text}'}, status=response.status_code)
    
    except requests.exceptions.RequestException as e:
        return JsonResponse({'error': f'Erro de conexão com a API do Forvo: {str(e)}'}, status=500)
