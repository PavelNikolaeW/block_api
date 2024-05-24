from django.urls import path
from .views import RegisterView, BlockView, BlockChangeLogView, RootBlockView, DeleteBlockView

app_name = 'api'

urlpatterns = [
    path('block/', BlockView.as_view(), name='block'),
    path('root-block/', RootBlockView.as_view(), name='root-block'),
    path('remove-block/', DeleteBlockView.as_view(), name='remove-block'),
    path('block/<int:pk>/', BlockView.as_view(), name='block-id'),
    path('block/changelog/<int:pk>/', BlockChangeLogView.as_view(), name='change-log'),
    path('register/', RegisterView.as_view(), name='register'),
]
