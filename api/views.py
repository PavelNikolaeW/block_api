import json
import logging
from pprint import pprint

from django.contrib.auth import get_user_model
from django.db import connection
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken

from .models import Block, BlockChangeLog
from .serializers import (RegisterSerializer,
                          BlockSerializer,
                          ChangeLogSerializer,
                          UserSerializer,
                          BlockCreateSerializer)
from .query import get_blocks_query

User = get_user_model()

logger = logging.getLogger(__name__)

INFORM_BLOCK_ID = 2
INFORM_BLOCK_USER_ID = 2


class RegisterView(APIView):
    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            # todo в дочерние блоки можно добавить обучающую инфу и общие шаблоны использования
            block_data = {'creator': user.id,
                          'text': user.username,
                          'access_type': 'private'}
            logger.info(block_data)
            block_serializer = BlockSerializer(data=block_data)
            block_serializer.is_valid()
            logger.info(block_serializer.errors)
            block = block_serializer.save()
            refresh = RefreshToken.for_user(user)
            return Response({
                'refresh': str(refresh),
                'access': str(refresh.access_token),
                'message': 'User created successfully with tokens',
                'block_id': block.id

            }, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class RootBlockView(APIView):
    def get(self, request):
        user = request.user
        if user.is_authenticated:
            block_id = user.blocks.first().id
            print(user.id, block_id)
            data = get_flat_map_blocks(user.id, block_id)
            return Response(data, status=status.HTTP_200_OK)
        data = get_flat_map_blocks(INFORM_BLOCK_USER_ID, INFORM_BLOCK_ID)
        return Response(data, status=status.HTTP_203_NON_AUTHORITATIVE_INFORMATION)


class DeleteBlockView(APIView):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.errors = {'errors': []}
        self.parent = {}
        self.child = {}

    def delete(self, request):
        user = request.user
        if user.is_authenticated:
            if not self._is_valid(request.data):
                return Response(self.errors, status=status.HTTP_400_BAD_REQUEST)

            block = Block.objects.get(pk=self.parent['id'])
            if not self._check_user_permissions(user, block):
                return Response(
                    {"error": f"You do not have permission to update this block {self.parent['id']}"},
                    status=status.HTTP_403_FORBIDDEN)

            is_updated_parent_or_err = self._update_parent(block, request)
            if not isinstance(is_updated_parent_or_err, bool):
                return Response(is_updated_parent_or_err, status=status.HTTP_400_BAD_REQUEST)

            child_block = Block.objects.get(pk=self.child['id'])
            if not self._check_user_permissions(user, child_block):
                return Response(
                    {"error": f"You do not have permission to delete this block. {self.child['id']}"},
                    status=status.HTTP_403_FORBIDDEN)

            parent_count = child_block.parent_blocks.count()
            if parent_count == 0:
                # Удаление блока, если у него больше нет родителей
                child_block.delete()
                return Response(status=status.HTTP_204_NO_CONTENT)
            else:
                return Response({'message': 'This block removed from parent'}, status=status.HTTP_204_NO_CONTENT)

        return Response(status=status.HTTP_401_UNAUTHORIZED)

    def _update_parent(self, parent, request):
        serializer = BlockSerializer(parent, data=self.parent, partial=True)
        if serializer.is_valid():
            serializer.save()
            return True
        return serializer.errors

    def _check_user_permissions(self, user, block):
        if block.creator == user:
            return True

        if block.editable_by_users.filter(id=user.id).exists():
            return True
        return False

    def _is_valid(self, data):
        self.parent = data.get('parent')
        parent_id = self.parent.get('id')
        parent_class_list = self.parent.get('classList')
        self.child = data.get('child')
        child_id = self.child.get('id')
        if not parent_id:
            self.errors['errors'].append('Parent ID is required')
        if not child_id:
            self.errors['errors'].append('Child ID is required')
        if not parent_class_list:
            self.errors['errors'].append('Parent class list is required')

        if self.errors['errors']:
            return False

        return True


class BlockView(APIView):
    def get(self, request, pk=None):
        user = request.user
        if user.is_authenticated:
            print(user.id, pk)
            data = get_flat_map_blocks(user.id, pk)
            print(data)
            return Response(data, status=status.HTTP_200_OK)

        data = get_flat_map_blocks(2, 2)
        return Response(data, status=status.HTTP_203_NON_AUTHORITATIVE_INFORMATION)

    def patch(self, request, pk=None):
        user = request.user
        print(request.data)
        if not user.is_authenticated:
            return Response({}, status=status.HTTP_401_UNAUTHORIZED)

        try:
            block = Block.objects.get(pk=pk)
        except Block.DoesNotExist:
            return Response({'error': 'Object not found.'}, status=status.HTTP_404_NOT_FOUND)

        if user not in block.editable_by_users.all() and block.access_type != 'public_editable':
            return Response({'error': 'You do not have permission to edit this block.'},
                            status=status.HTTP_403_FORBIDDEN)

        serializer = BlockSerializer(block, data=request.data, partial=True)
        print(request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, pk=None):
        user = request.user
        if not user.is_authenticated:
            return Response({}, status=status.HTTP_401_UNAUTHORIZED)

        # parent_id = request.data.get('parent_id')
        # if not parent_id:
        #     return Response(
        #         {"error": "parent_id is field required"}, status=status.HTTP_400_BAD_REQUEST)

        block = get_object_or_404(Block, pk=pk)
        # parent = get_object_or_404(Block, pk=parent_id)

        # Проверка прав пользователя
        if not self._check_user_permissions(user, block):
            return Response(
                {"error": "You do not have permission to delete this block."},
                status=status.HTTP_403_FORBIDDEN
            )

        # Удаляем ребенка у родителя
        # self._update_parent_remove_child(parent, block)

        # Проверка количества родителей после обновления
        parent_count = block.parent_blocks.count()
        if parent_count == 0:
            # Удаление блока, если у него больше нет родителей
            block.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)

        return Response(status=status.HTTP_200_OK)

    def post(self, request):
        user = request.user
        if not user.is_authenticated:
            return Response({}, status=status.HTTP_401_UNAUTHORIZED)

        request.data['creator'] = user.id
        print(request.data)
        serializer = BlockSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            print(serializer.data)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def _update_parent_remove_child(self, parent, child):
        parent.children.remove(child)
        parent.save()
        return

        # serializer = BlockCreateSerializer(data=request.data, user=user)
        # if serializer.is_valid():
        #     parent, child = serializer.save()
        # else:
        #     return Response(serializer.errors, status=serializer.status)

        # return Response({'parent': parent, 'child': child}, status=status.HTTP_201_CREATED)


class BlockChangeLogView(APIView):
    def get(self, request, pk):
        user = request.user
        if not user.is_authenticated:
            return Response({}, status=status.HTTP_401_UNAUTHORIZED)
        try:
            block = Block.objects.get(pk=pk)
        except Block.DoesNotExist:
            return Response({'error': 'Block not found.'}, status=status.HTTP_404_NOT_FOUND)

        if user not in block.visible_to_users.all() and (block.access_type != 'public' and
                                                         block.access_type != 'public_editable'):
            return Response({'error': 'You do not have permission to view this block.'},
                            status=status.HTTP_401_UNAUTHORIZED)

        try:
            change_log = BlockChangeLog.objects.filter(block=pk)
        except BlockChangeLog.DoesNotExist:
            return Response({'error': 'Change log not found.'}, status=status.HTTP_404_NOT_FOUND)

        serializer = ChangeLogSerializer(change_log, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


def get_flat_map_blocks(user_id, block_id):
    print(user_id, block_id)
    with connection.cursor() as cursor:
        cursor.execute(get_blocks_query, {'user_id': user_id, 'block_id': block_id})
        columns = [col[0] for col in cursor.description]
        json_fields = ['content_classList', 'classList', 'children_position', 'properties']  # Поля, ожидаемые как JSON

        result = {}
        for row in cursor.fetchall():
            row_dict = dict(zip(columns, row))
            row_dict['paths'] = row_dict['paths'].split(';')
            # Преобразование строк, содержащих JSON, в объекты Python
            for field in json_fields:
                try:
                    row_dict[field] = json.loads(row_dict[field])
                except json.JSONDecodeError:
                    print(f"Error decoding JSON for {field} in row {row[0]}")

            result[row[0]] = row_dict

        return result

#
#         request.data.pop('id')
#         request.data.pop('created_at')
#         request.data.pop('updated_at')
#         request.data.pop('creator_id')
#         request.data.pop('direct_status')
#         request.data.pop('effective_status')
#         request.data.pop('is_ambiguous')
#         request.data.pop('is_fully_loaded')
#         request.data.pop('paths')
#         request.data.pop('styleObj')
#         request.data.pop('children')
#         old_data = {key: getattr(block, key) for key in request.data if
#                     hasattr(block, key) and getattr(block, key) != request.data[key]}
#
#         change_log_data = {
#             'block': block.id,
#             'content_change': {
#                 'old_data': old_data,
#                 'new_data': request.data
#             }
#         }
#         change_log_serializer = ChangeLogSerializer(data=change_log_data)
#         if change_log_serializer.is_valid():
#             change_log_serializer.save(changed_by=user)
#         else:
#             return Response({'errors': change_log_serializer.errors, 'test': 'test'},
#                             status=status.HTTP_400_BAD_REQUEST)
