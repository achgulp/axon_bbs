# Axon BBS - A modern, anonymous, federated bulletin board system.
# Copyright (C) 2025 Achduke7
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
# See the GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <https://www.gnu.org/licenses/>.


# Full path: axon_bbs/api/views/auth_views.py
from rest_framework import generics, permissions, status, views
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from django.http import JsonResponse, HttpResponse
from django.contrib.auth import get_user_model
from django.db import IntegrityError
from PIL import Image
from django.core.files.base import ContentFile
import io
import base64
import logging
from cryptography.hazmat.primitives import serialization
from cryptography.exceptions import UnsupportedAlgorithm
from rest_framework_simplejwt.tokens import RefreshToken
from django.conf import settings


from ..serializers import UserSerializer
from core.models import TrustedInstance, FileAttachment, FederatedAction
from core.services.identity_service import IdentityService, DecryptionError
from core.services.service_manager import service_manager
from core.services.encryption_utils import generate_checksum

logger = logging.getLogger(__name__)
User = get_user_model()


class RegisterView(generics.CreateAPIView):
    queryset = User.objects.all()
    permission_classes = (permissions.AllowAny,)
    serializer_class = UserSerializer

    def create(self, request, *args, **kwargs):
        username = request.data.get('username')
        nickname = request.data.get('nickname')

        # Check for nickname conflict
        conflicting_user_by_nickname = User.objects.filter(nickname__iexact=nickname).first()
        if conflicting_user_by_nickname:
            if not conflicting_user_by_nickname.is_active:
                return Response(
                    {"error": "nickname_exists_as_federated", "detail": f"The nickname '{nickname}' is reserved by a federated user. You can claim this account if you have the private key."},
                    status=status.HTTP_409_CONFLICT
                )
            else:
                return Response({"error": "A user with that nickname already exists."}, status=status.HTTP_400_BAD_REQUEST)

        # Check for username conflict
        conflicting_user_by_username = User.objects.filter(username__iexact=username).first()
        if conflicting_user_by_username:
             if not conflicting_user_by_username.is_active:
                 return Response(
                    {"error": "username_exists_as_federated", "detail": f"The username '{username}' is reserved. Try claiming by nickname."},
                    status=status.HTTP_409_CONFLICT
                )
             else:
                return Response({"error": "A user with that username already exists."}, status=status.HTTP_400_BAD_REQUEST)

        # If no conflicts, proceed with registration.
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)


class ClaimAccountView(views.APIView):
    permission_classes = [permissions.AllowAny]
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request, *args, **kwargs):
        nickname_to_claim = request.data.get('nickname')
        new_username = request.data.get('username')
        new_password = request.data.get('new_password')
        key_file = request.FILES.get('key_file')
        key_file_password = request.data.get('key_file_password', None)

        if not all([nickname_to_claim, new_username, new_password, key_file]):
            return Response({"error": "Username, nickname, new password, and private key file are required."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            user_to_claim = User.objects.get(nickname__iexact=nickname_to_claim, is_active=False)
        except User.DoesNotExist:
            return Response({"error": "No inactive, federated user found with that nickname."}, status=status.HTTP_404_NOT_FOUND)
        
        # Check if the desired new username is already taken by a different active user
        if User.objects.filter(username__iexact=new_username).exclude(pk=user_to_claim.pk).exists():
            return Response({"error": f"The username '{new_username}' is already in use by another account."}, status=status.HTTP_409_CONFLICT)

        try:
            private_key_pem = key_file.read()
            key_password_bytes = key_file_password.encode() if key_file_password else None
            try:
                private_key = serialization.load_pem_private_key(private_key_pem, password=key_password_bytes)
            except TypeError:
                return Response({"error": "Password mismatch for private key. Provide a password if the key is encrypted, or leave it blank if not."}, status=status.HTTP_400_BAD_REQUEST)
            
            derived_public_key = private_key.public_key()
            
            derived_public_key_pem = derived_public_key.public_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PublicFormat.SubjectPublicKeyInfo
            ).decode('utf-8').strip()

            if derived_public_key_pem != user_to_claim.pubkey.strip():
                return Response({"error": "Private key does not match the public key on record for this user."}, status=status.HTTP_403_FORBIDDEN)

            user_to_claim.username = new_username
            user_to_claim.nickname = nickname_to_claim 
            user_to_claim.is_active = True
            user_to_claim.set_password(new_password)
            user_to_claim.save()

            identity_service = IdentityService(user=user_to_claim)
            identity_service.create_storage_from_key(new_password, private_key_pem.decode('utf-8'))

            refresh = RefreshToken.for_user(user_to_claim)
            
            return Response({
                'status': 'Account claimed successfully.',
                'refresh': str(refresh),
                'access': str(refresh.access_token),
            }, status=status.HTTP_200_OK)

        except (ValueError, TypeError, UnsupportedAlgorithm) as e:
            return Response({"error": f"Invalid private key file format or incorrect key password: {e}"}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            logger.error(f"Unexpected error during account claim for {nickname_to_claim}: {e}", exc_info=True)
            return Response({"error": "An unexpected server error occurred."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class LogoutView(views.APIView):
    permission_classes = [permissions.IsAuthenticated]
    def post(self, request, *args, **kwargs):
        if 'unencrypted_priv_key' in request.session:
            del request.session['unencrypted_priv_key']
        return Response({"status": "session cleared"}, status=status.HTTP_200_OK)

class UnlockIdentityView(views.APIView):
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request, *args, **kwargs):
        user, password = request.user, request.data.get('password')
        if not password: return Response({"error": "Password is required."}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            identity_service = IdentityService(user=user)
            private_key = identity_service.get_unlocked_private_key(password)
            if not private_key:
                raise DecryptionError("Failed to unlock with provided password.")
            
            request.session['unencrypted_priv_key'] = private_key
            logger.info(f"Identity unlocked for user {user.username}")
            return Response({"status": "identity unlocked"}, status=status.HTTP_200_OK)
        except DecryptionError as e:
            logger.warning(f"Failed unlock attempt for {user.username}: {e}")
            return Response({"error": "Unlock failed. Please check your password."}, status=status.HTTP_401_UNAUTHORIZED)
        except Exception as e:
            logger.error(f"Failed to unlock identity for {user.username}: {e}", exc_info=True)
            return Response({"error": "An unexpected error occurred during unlock."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class ImportIdentityView(views.APIView):
    permission_classes = [permissions.IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def post(self, request, *args, **kwargs):
        return Response({"error": "Import functionality is not yet updated for the new identity system."}, status=status.HTTP_501_NOT_IMPLEMENTED)

class ExportIdentityView(views.APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, *args, **kwargs):
        password = request.data.get('password')
        if not password:
            return Response({"error": "Password is required to export your key."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            identity_service = IdentityService(user=request.user)
            private_key_pem = identity_service.get_unlocked_private_key(password)
            
            if not private_key_pem:
                raise DecryptionError("Failed to unlock key for export.")

            response = HttpResponse(private_key_pem, content_type='application/x-pem-file')
            response['Content-Disposition'] = f'attachment; filename="{request.user.username}_axon_identity.pem"'
            return response

        except DecryptionError:
            return Response({"error": "Export failed. The password provided was incorrect."}, status=status.HTTP_403_FORBIDDEN)
        except Exception as e:
            logger.error(f"Failed to export identity for {request.user.username}: {e}", exc_info=True)
            return Response({"error": "An unexpected server error occurred during export."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class UpdateNicknameView(views.APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, *args, **kwargs):
        nickname = request.data.get('nickname')
        if not nickname:
            return Response({"error": "Nickname cannot be empty."}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            user = request.user
            user.nickname = nickname
            user.save()

            avatar_attachment = FileAttachment.objects.filter(author=user, filename=f'{user.username}_avatar.png').first()

            FederatedAction.objects.create(
                action_type='update_profile',
                pubkey_target=user.pubkey,
                status='pending_approval',
                action_details={
                    'nickname': user.nickname,
                    'karma': user.karma,
                    'avatar_hash': avatar_attachment.manifest.get('content_hash') if avatar_attachment else None
                }
            )
            return Response({"status": "Nickname update submitted for approval.", "nickname": nickname}, status=status.HTTP_200_OK)
        except IntegrityError:
            return Response({"error": "This nickname is already taken."}, status=status.HTTP_409_CONFLICT)
        except Exception as e:
            logger.error(f"Could not update nickname for {request.user.username}: {e}", exc_info=True)
            return Response({"error": "An error occurred while updating the nickname."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class UserProfileView(views.APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, *args, **kwargs):
        user = request.user
        return Response({
            "username": user.username,
            "nickname": user.nickname,
            "pubkey": user.pubkey,
            "avatar_url": request.build_absolute_uri(user.avatar.url) if user.avatar else None,
            "karma": user.karma,
            "is_moderator": user.is_moderator,
            "timezone": user.timezone,
        })

class UploadAvatarView(views.APIView):
    permission_classes = [permissions.IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request, *args, **kwargs):
        if 'avatar' not in request.FILES:
            return Response({"error": "No avatar file provided."}, status=status.HTTP_400_BAD_REQUEST)
        
        file = request.FILES['avatar']
        
        if file.size > 1024 * 1024:
            return Response({"error": "Avatar file size cannot exceed 1MB."}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            img = Image.open(file)
            
            if img.mode != 'RGB':
                img = img.convert('RGB')

            img.thumbnail((128, 128))
            
            thumb_io = io.BytesIO()
            img.save(thumb_io, format='PNG')
            
            user = request.user
            
            file_content = {
                "type": "file", "filename": f'{user.username}_avatar.png', "content_type": 'image/png',
                "size": thumb_io.tell(), "data": base64.b64encode(thumb_io.getvalue()).decode('ascii')
            }
            _content_hash, manifest = service_manager.bitsync_service.create_encrypted_content(file_content)
            
            FileAttachment.objects.update_or_create(
                author=user,
                filename=f'{user.username}_avatar.png',
                defaults={
                    'content_type': 'image/png',
                    'size': thumb_io.tell(),
                    'manifest': manifest
                }
            )

            user.avatar.save(f'{user.username}_avatar.png', ContentFile(thumb_io.getvalue()), save=False)
            user.save(update_fields=['avatar'])
 
            FederatedAction.objects.create(
                action_type='update_profile',
                pubkey_target=user.pubkey,
                status='pending_approval',
                action_details={
                    'nickname': user.nickname,
                    'karma': user.karma,
                    'avatar_hash': manifest.get('content_hash')
                }
            )

            return Response({"status": "Avatar update submitted for approval.", "avatar_url": user.avatar.url})

        except Exception as e:
            logger.error(f"Could not process avatar for {request.user.username}: {e}")
            return Response({"error": "Invalid image file. Please upload a valid PNG, JPG, or GIF."}, status=status.HTTP_400_BAD_REQUEST)

class GetPublicKeyView(views.APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request, *args, **kwargs):
        try:
            local_instance = TrustedInstance.objects.get(
                encrypted_private_key__isnull=False,
                is_trusted_peer=False
            )
            if local_instance.pubkey:
                return JsonResponse({"public_key": local_instance.pubkey})
            else:
                return Response({"error": "Local instance has no public key."}, status=status.HTTP_404_NOT_FOUND)
        except TrustedInstance.DoesNotExist:
            return Response({"error": "Local instance not configured."}, status=status.HTTP_404_NOT_FOUND)
        except TrustedInstance.MultipleObjectsReturned:
            return Response({"error": "Configuration error: Multiple local instances found."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class GetSecurityQuestionsView(views.APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request, *args, **kwargs):
        username = request.data.get('username')
        if not username:
            return Response({'error': 'Username is required.'}, status=status.HTTP_400_BAD_REQUEST)
        try:
            user = User.objects.get(username=username)
            identity_service = IdentityService(user=user)
            questions = identity_service.get_security_questions()
            if questions:
                return Response(questions)
            else:
                return Response({"error": "User does not have manifest-based recovery configured."}, status=status.HTTP_400_BAD_REQUEST)
        except User.DoesNotExist:
            return Response({"error": "User not found."}, status=status.HTTP_404_NOT_FOUND)

class SubmitRecoveryView(views.APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request, *args, **kwargs):
        username = request.data.get('username')
        answer_1 = request.data.get('answer_1')
        answer_2 = request.data.get('answer_2')
        new_password = request.data.get('new_password')

        if not all([username, answer_1, answer_2, new_password]):
            return Response({"error": "All fields are required."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            user = User.objects.get(username=username)
            identity_service = IdentityService(user=user)
            
            success = identity_service.recover_identity_with_answers(answer_1, answer_2, new_password)
            
            if success:
                user.set_password(new_password)
                user.save()
                return Response({"status": "Password has been successfully reset."})
            else:
                return Response({"error": "Recovery failed. One or more answers were incorrect."}, status=status.HTTP_400_BAD_REQUEST)
        except User.DoesNotExist:
            return Response({"error": "User not found."}, status=status.HTTP_404_NOT_FOUND)

class ChangePasswordView(views.APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, *args, **kwargs):
        user = request.user
        old_password = request.data.get('old_password')
        new_password = request.data.get('new_password')

        if not all([old_password, new_password]):
            return Response({"error": "All fields are required."}, status=status.HTTP_400_BAD_REQUEST)
        
        if not user.check_password(old_password):
            return Response({"error": "Your current password was incorrect."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            identity_service = IdentityService(user=user)
            # This re-uses the recovery mechanism to re-encrypt the master key with the new password
            success = identity_service.recover_identity_with_answers(None, None, new_password, use_password=True)
            if not success:
                 raise Exception("Failed to re-key identity manifest with new password.")

            user.set_password(new_password)
            user.save()
            return Response({"status": "Password changed successfully."})

        except Exception as e:
            logger.error(f"Error changing password for {user.username}: {e}")
            return Response({"error": "An unexpected error occurred while changing the password."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class ResetSecurityQuestionsView(views.APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, *args, **kwargs):
        user = request.user
        password = request.data.get('current_password')
        sq1 = request.data.get('security_question_1')
        sa1 = request.data.get('security_answer_1')
        sq2 = request.data.get('security_question_2')
        sa2 = request.data.get('security_answer_2')

        if not all([password, sq1, sa1, sq2, sa2]):
            return Response({"error": "All fields are required."}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            identity_service = IdentityService(user=user)
            success = identity_service.reset_security_questions(password, sq1, sa1, sq2, sa2)

            if success:
                return Response({"status": "Security questions have been reset successfully."})
            else:
                return Response({"error": "Could not reset security questions. Please check your password."}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            logger.error(f"Error resetting security questions for {user.username}: {e}")
            return Response({"error": "An unexpected server error occurred."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class UpdateTimezoneView(views.APIView):
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request, *args, **kwargs):
        user = request.user
        timezone = request.data.get('timezone')
        
        if not timezone:
            return Response({"error": "Timezone is a required field."}, status=status.HTTP_400_BAD_REQUEST)
        
        # A full implementation would validate against a list of IANA timezones
        user.timezone = timezone
        user.save(update_fields=['timezone'])
        
        return Response({"status": "Timezone updated successfully."})


class GetDisplayTimezoneView(views.APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request, *args, **kwargs):
        # If the user is logged in and has a specific timezone set, use that.
        if request.user.is_authenticated and request.user.timezone:
            return Response({'timezone': request.user.timezone})
        
        # Otherwise, fall back to the admin-defined default.
        return Response({'timezone': settings.DISPLAY_TIMEZONE})
