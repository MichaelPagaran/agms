from django.dispatch import Signal

# Signal sent when a user accepts an invite and their account is created
# Provides: user (User instance), invite (UserInvite instance)
user_accepted_invite = Signal()
