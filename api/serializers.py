from rest_framework import serializers, status
from django.contrib.auth.password_validation import validate_password
from django.contrib.auth.models import User
from .models import (
    Block,
    BlockChangeLog,
    Group,
    LAYOUT_CHOICES,
    ACCESS_TYPE_CHOICES
)


def default_content_class_list():
    return ['grid-row_1', 'grid-column_1-M1']


def default_class_list():
    return ['grid-template-columns_1fr', 'grid-template-rows_1fr', ]


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=True, style={'input_type': 'password'})

    class Meta:
        model = User
        fields = ('username', 'password', 'email')

    def validate_password(self, value):
        # validate_password(value)
        return value

    def create(self, validated_data):
        user = User.objects.create_user(
            username=validated_data['username'],
            email=validated_data.get('email'),
            password=validated_data['password']
        )
        return user


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ('id', 'username', 'email')


class BlockSerializer(serializers.ModelSerializer):
    visible_to_users = serializers.PrimaryKeyRelatedField(
        many=True,
        queryset=User.objects.all(),
        required=False
    )
    editable_by_users = serializers.PrimaryKeyRelatedField(
        many=True,
        queryset=User.objects.all(),
        required=False
    )
    children = serializers.PrimaryKeyRelatedField(
        many=True,
        queryset=Block.objects.all(),
        required=False
    )
    children_position = serializers.JSONField(default=dict)
    text = serializers.CharField(allow_blank=True, required=False)
    content_classList = serializers.JSONField(default=default_content_class_list)
    image = serializers.ImageField(use_url=True, allow_null=True, required=False)
    classList = serializers.JSONField(default=default_class_list)
    layout = serializers.ChoiceField(choices=LAYOUT_CHOICES, default='default')
    access_type = serializers.ChoiceField(choices=ACCESS_TYPE_CHOICES, default='inherited')
    color = serializers.CharField(allow_blank=True, default='default_color', required=False)
    properties = serializers.JSONField(default=dict)

    def validate_color(self, value):
        return value if value else ''

    class Meta:
        model = Block
        fields = '__all__'


class BlockCreateSerializer:

    def __init__(self, data, user):
        self.status = None
        self.parent = None
        self.errors = {}
        self.data = data
        self.user = user

    def is_valid(self):
        parent_id = self.data.get('parent')
        children_position = self.data.get('children_position')
        class_list = self.data.get('classList')
        parent_block = None
        try:
            parent_block = Block.objects.get(pk=parent_id)
        except Block.DoesNotExist:
            self.errors['not_found'] = 'Parent block not found'
            self.errors['parent'] = 'Parent block not found'

        if (parent_block is not None and
                self.user not in parent_block.editable_by_users.all() and
                parent_block.access_type != 'public_editable'):
            self.errors['access'] = "You do not have permission to edit this block."
            self.status = status.HTTP_403_FORBIDDEN

        if not children_position:
            self.errors['children_position'] = 'Children position is required.'
            self.status = status.HTTP_400_BAD_REQUEST

        if not class_list:
            self.errors['classList'] = 'classList is required.'
            self.status = status.HTTP_400_BAD_REQUEST

        self.parent = parent_block

        if self.errors:
            return False
        return True

    def save(self):
        child = Block.objects.create(creator=self.user.id,
                                     classList=default_class_list(),
                                     content_classList=default_content_class_list())
        child.save()
        self.parent.children.add(child)
        self.parent.children_position = self.data.get('children_position')
        self.parent.classList = self.data.get('classList')
        self.parent.save()
        return self.parent, child


class ChangeLogSerializer(serializers.ModelSerializer):
    block = serializers.PrimaryKeyRelatedField(required=True, queryset=Block.objects.all())
    changed_by = UserSerializer(read_only=True)
    content_change = serializers.JSONField(default=dict)

    class Meta:
        model = BlockChangeLog
        fields = '__all__'
