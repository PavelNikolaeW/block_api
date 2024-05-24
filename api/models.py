from django.db import models

LAYOUT_CHOICES = (('default', 'Default'), ('horizontal', 'Horizontal'), ('vertical', 'Vertical'), ('table', 'Table'))
ACCESS_TYPE_CHOICES = (('private', 'Private'),
                       ('public', 'Public'),
                       ('inherited', 'Inherited'),
                       ('public_ed', 'Public Editable'))


def default_content_class_list():
    return ['grid-row_1', 'grid-column_1-M1']


def default_class_list():
    return ['grid-template-columns_1fr', 'grid-template-rows_1fr', ]


class Block(models.Model):
    creator = models.ForeignKey('auth.User', related_name='blocks', on_delete=models.CASCADE)

    access_type = models.CharField(max_length=10, choices=ACCESS_TYPE_CHOICES, default='inherited')
    visible_to_users = models.ManyToManyField('auth.User', related_name='visible_blocks', blank=True)
    editable_by_users = models.ManyToManyField('auth.User', related_name='editable_blocks', blank=True)

    children = models.ManyToManyField('self', symmetrical=False, related_name='parent_blocks', blank=True)
    children_position = models.JSONField(blank=True, null=True, default=dict)

    text = models.TextField(null=True, blank=True, default='')
    content_classList = models.JSONField(blank=True, null=True, default=default_content_class_list)
    image = models.ImageField(upload_to='images/', null=True, blank=True)

    classList = models.JSONField(blank=True, null=True, default=default_class_list)

    layout = models.CharField(max_length=50, choices=LAYOUT_CHOICES, blank=True, default='default')
    color = models.CharField(max_length=20, null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    properties = models.JSONField(blank=True, null=True, default=dict)

    def save(self, *args, **kwargs):
        is_new = self._state.adding
        super().save(*args, **kwargs)  # Сначала сохраняем, чтобы объект имел ID
        if is_new:
            self.visible_to_users.add(self.creator)
            self.editable_by_users.add(self.creator)
            # super().save(*args, **kwargs)  # Сохраняем объект снова, если нужно сохранить изменения после добавления M2M


class BlockChangeLog(models.Model):
    block = models.ForeignKey(Block, related_name='changes', on_delete=models.CASCADE)
    changed_by = models.ForeignKey('auth.User', related_name='changes_made', on_delete=models.CASCADE)
    changed_at = models.DateTimeField(auto_now_add=True)
    content_change = models.JSONField(blank=True, null=True, default=dict)


class Group(models.Model):
    name = models.CharField(max_length=100)
    members = models.ManyToManyField('auth.User', related_name='user_groups')
    visible_blocks = models.ManyToManyField(Block, related_name='group_visible_blocks')
    editable_blocks = models.ManyToManyField(Block, related_name='group_editable_blocks')
