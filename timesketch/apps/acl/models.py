# Copyright 2014 Google Inc. All rights reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""Django database model for creating Access Control Lists."""

from django.db import models
from django.core.exceptions import ObjectDoesNotExist
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.contrib.auth.models import User


class AccessControlEntry(models.Model):
    """Model for an access control entry."""
    user = models.ForeignKey(User, blank=True, null=True)
    # Permissions
    permission_read = models.BooleanField(default=False)
    permission_write = models.BooleanField(default=False)
    permission_delete = models.BooleanField(default=False)
    # This is the django content type framework for generic relations
    content_type = models.ForeignKey(ContentType)
    object_id = models.PositiveIntegerField()
    content_object = GenericForeignKey()
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)

    def __unicode__(self):
        return 'ACE for %s on %s %s' % (
            self.user, self.content_type, self.content_object)


class AccessControlMixIn(object):
    def is_public(self):
        """Function to determine if the ACL is open to everyone for the
        specific object.

        Returns:
            Boolean value to indicate if the object is readable by everyone.
        """
        try:
            self.acl.get(user=None, permission_read=True)
            return True
        except ObjectDoesNotExist:
            return False

    def make_public(self, user):
        """Function to make object public.

        Args:
            user. user object (instance of django.contrib.auth.models.User)
        """
        # First see if the user is allowed to make this change.
        if not self.can_write(user):
            return
        try:
            ace = self.acl.get(user=None)
            if not ace.read:
                ace.permission_read = True
                ace.save()
        except ObjectDoesNotExist:
            self.acl.create(user=None, permission_read=True)

    def make_private(self, user):
        """Function to make object private.

        Args:
            user. user object (instance of django.contrib.auth.models.User)
        """
        # First see if the user is allowed to make this change.
        if not self.can_write(user):
            return
        try:
            ace = self.acl.get(user=None)
            ace.delete()
        except ObjectDoesNotExist:
            pass

    def can_read(self, user):
        """Function to determine if the user have read access to the specific
        object.

        Args:
            user. user object (instance of django.contrib.auth.models.User)
        Returns:
            Boolean value to indicate if the object is readable by user.
        """
        # Is the objects owner is same as user or the object is public
        # then access is granted.
        if self.user == user:
            return True
        if self.is_public():
            return True
        # Private object. If we have a ACE for the user on this object
        # and that ACE has read rights. If so, then access is granted.
        try:
            ace = self.acl.get(user=user)
        except ObjectDoesNotExist:
            return False
        if ace.permission_read:
            return True
        return False

    def can_write(self, user):
        """Function to determine if the user have write access to the object.

        Args:
            user. user object (instance of django.contrib.auth.models.User)
        Returns:
            Boolean value to indicate if the object is writable by user.
        """
        # Is the objects owner is same as user or the object is public then
        # write access is granted.
        if self.user == user:
            return True
        # Private object. If we have a ACE for the user on this object and
        # that ACE has write rights. If so, then access is granted.
        try:
            self.acl.get(user=user, permission_write=True)
            return True
        except ObjectDoesNotExist:
            return False

    def get_collaborators(self):
        """Function to get all users that has rw access to this sketch.

        Returns:
            A set() of User objects
        """
        collaborators_set = set()
        for ace in self.acl.all():
            if ace.user and not ace.user == self.user:
                collaborators_set.add(ace)
        return collaborators_set