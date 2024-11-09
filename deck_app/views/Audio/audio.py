from rest_framework.decorators import api_view
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from reverso_api.voice import ReversoVoiceAPI, get_voices
import os
from django.conf import settings


@csrf_exempt
@api_view(['POST'])
def get_pronunciations(request):
    word = request.data.get('word')
    if not word:
        return JsonResponse({'success': False,
                             'message': 'A palavra é obrigatória.'})

    try:
        native_voices = {
            'US': ['Karen22k', 'Kenny22k', 'Sharon22k', 'Will22k'],
            'British': ['Graham22k', 'Lucy22k', 'Peter22k', 'Rachel22k']
        }
        # Diretório onde os áudios serão salvos
        custom_path = os.path.join(settings.MEDIA_ROOT, 'audios')
        os.makedirs(custom_path, exist_ok=True)

        pronunciations = []
        voices = get_voices()  # Obtenha a lista de vozes disponíveis

        for language, voice_list in voices.items():
            if language in native_voices:
                filtered_voices = [
                    voice for voice in voice_list if voice.name in native_voices[language]]

                for voice in filtered_voices:
                    audio_file_path = os.path.join(
                        custom_path, f"{word}_{voice.name}.mp3")
                    voice_api = ReversoVoiceAPI(text=word, voice=voice)
                    voice_api.write_to_file(audio_file_path)
                    pronunciations.append({
                        'voice': {
                            'name': voice.name,
                            'language': voice.language,
                            'gender': voice.gender
                        },
                        'audio_file': audio_file_path
                    })
        return JsonResponse({
            'success': True,
            'message': 'Pronúncias obtidas com sucesso.',
            'pronunciations': pronunciations
        })
    except Exception as e:
        return JsonResponse({'success': False,
                             'message': f"Erro ao buscar a pronúncia: {str(e)}"})