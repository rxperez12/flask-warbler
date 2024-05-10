"""User model tests."""

import os
from unittest import TestCase

from app import app, CURR_USER_KEY
from models import db, dbx, User, Message
from sqlalchemy import exc 

# To run the tests, you must provide a "test database", since these tests
# delete & recreate the tables & data. In your shell:
#
# Do this only once:
#   $ createdb warbler_test
#
# To run the tests using that test data:
# $ DATABASE_URL=postgresql:///warbler_test python3 -m unittest

if not app.config['SQLALCHEMY_DATABASE_URI'].endswith("_test"):
    raise Exception("\n\nMust set DATABASE_URL env var to db ending with _test")

# NOW WE KNOW WE'RE IN THE RIGHT DATABASE, SO WE CAN CONTINUE
app.app_context().push()
db.drop_all()
db.create_all()


class UserModelTestCase(TestCase):
    def setUp(self):
        dbx(db.delete(User))
        db.session.commit()

        u1 = User.signup("u1", "u1@email.com", "password", None)
        db.session.flush()
        
        u2 = User.signup("u2", "u2@email.com", "password", None)
        db.session.flush()
        
        m1 = Message(text="m1-text", user_id=u2.id)
        
        db.session.add_all([m1])
        db.session.commit()
        
        self.u1_id = u1.id
        self.m1_id = m1.id
        
        self.u2_id = u2.id

    def tearDown(self):
        db.session.rollback()

    def test_user_model(self):
        u1 = db.session.get(User, self.u1_id)

        # User should have no messages & no followers
        self.assertEqual(len(u1.messages), 0)
        self.assertEqual(len(u1.followers), 0)

class UserModelIsFollowingTestCase(UserModelTestCase):
    def test_is_following_and_is_followed_by(self):     
        u1 = db.session.get(User, self.u1_id)
        u2 = db.session.get(User, self.u2_id)
        
        u1.follow(u2)
        db.session.commit()
        
        self.assertEqual(u1.is_following(u2), True)
        self.assertEqual(u2.is_followed_by(u1), True)
        
        u1.unfollow(u2)
        db.session.commit()
        
        self.assertEqual(u1.is_following(u2), False)
        self.assertEqual(u2.is_followed_by(u1), False)
        
    def test_is_following_and_is_followed_by_no_followers(self):
        u1 = db.session.get(User, self.u1_id)
        u2 = db.session.get(User, self.u2_id)
        
        self.assertEqual(u1.is_following(u2), False)
        self.assertEqual(u2.is_followed_by(u1), False)
        
    def test_following_and_followers_property(self):
        u1 = db.session.get(User, self.u1_id)
        u2 = db.session.get(User, self.u2_id)
        
        u1.follow(u2)
        db.session.commit()
        
        u2_followers = u2.followers
        self.assertIn(u1, u2_followers)
        
        u1_following = u1.following
        self.assertIn(u2, u1_following)
        

class UserModelSignupTestCase(UserModelTestCase):
    def test_user_signup(self):
        u3 = User.signup("u3", "u3@email.com", "password", None)
        db.session.commit()
        
        q_user = db.select(User).where(User.id == u3.id)
        users = dbx(q_user).all()
        
        self.assertEqual(len(users), 1)
        
    def test_user_signup_bad_input(self):
        with self.assertRaises(ValueError) as e:
            User.signup("u3", "u3@email.com", None, None)
        
        self.assertEqual(str(e.exception), 'Password must be non-empty.')
        
class UserModelAuthenticateTestCase(UserModelTestCase):
    def test_authenticate(self):
        u1 = db.session.get(User, self.u1_id)
        self.assertEqual(User.authenticate("u1", "password"), u1)
        
    def test_authenticate_bad_password(self):
        self.assertEqual(User.authenticate("u1", "password123"), False)
        
    def test_authenticate_bad_username(self):
        self.assertEqual(User.authenticate("u3", "password"), False)
        
class UserModelLikeTestCase(UserModelTestCase):
    def test_add_and_remove_like(self):
        u1 = db.session.get(User, self.u1_id)
        u1.add_like(self.m1_id)
        db.session.commit()
        
        self.assertEqual(len(u1.likes), 1)
        
        u1.remove_like(self.m1_id)
        db.session.commit()
        
        self.assertEqual(len(u1.likes), 0)
        
    def test_liking_already_liked_message(self):
        u1 = db.session.get(User, self.u1_id)
        u1.add_like(self.m1_id)
        db.session.commit()
        
        # try to like same message again, catch IntegrityError
        with self.assertRaises(exc.IntegrityError) as e:
            u1.add_like(self.m1_id)
            db.session.commit()
            
        self.assertIn(
            "duplicate key value violates unique constraint", 
            str(e.exception)
        )
        
    def test_liked_messages_property(self):
        u1 = db.session.get(User, self.u1_id)
        m1 = db.session.get(Message, self.m1_id)
        u1.add_like(self.m1_id)
        db.session.commit()
        
        u1_liked_messages = u1.liked_messages
        self.assertIn(m1, u1_liked_messages)
        
        u1_liked_messages_ids = u1.liked_messages_ids
        self.assertIn(self.m1_id, u1_liked_messages_ids)
        