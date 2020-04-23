from .models import Collection

def user_collections(request):
    collections = []

    if request.user:
        collections = Collection.objects.filter(owners=request.user.id) 

    return {
            'user_collections': collections
        }
