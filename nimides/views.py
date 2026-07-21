from django.http import JsonResponse

def health_check(request):
    """
    Lightweight health check endpoint to keep the Render instance awake.
    Returns a 200 OK JSON response.
    """
    return JsonResponse({
        "status": "healthy",
        "message": "Server is active and running."
    })
