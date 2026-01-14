import os
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt

@csrf_exempt
def upload_recording(request):
    print("DEBUG: Upload endpoint hit")
    if request.method == 'POST':
        recording = request.FILES.get('recording')
        print(f"DEBUG: Files: {request.FILES.keys()}")
        if recording:
            # Generate filename or use provided one
            filename = request.POST.get('filename', 'recording.webm')
            # Sanitize filename (basic)
            filename = os.path.basename(filename)
            
            save_path = os.path.join('/home/dukejer/axon_bbs/recordings', filename)
            print(f"DEBUG: Saving to {save_path}, size: {recording.size}")
            
            try:
                with open(save_path, 'wb+') as destination:
                    for chunk in recording.chunks():
                        destination.write(chunk)
                print("DEBUG: Save success")
                return JsonResponse({'status': 'success', 'path': save_path})
            except Exception as e:
                print(f"DEBUG: Save error: {e}")
                return JsonResponse({'status': 'error', 'message': str(e)}, status=500)
                
        print("DEBUG: No file provided")
        return JsonResponse({'status': 'error', 'message': 'No file provided'}, status=400)
    return JsonResponse({'status': 'error', 'message': 'Invalid method'}, status=405)
