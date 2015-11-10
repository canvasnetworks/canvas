from canvas.tests.tests_helpers import CanvasTestCase, create_user, create_staff, create_group
    
class TestAuthorization(CanvasTestCase):
    def test_user_cannot_moderate_group(self):
        normal_user, group = create_user(), create_group()
        self.assertFalse(group.can_moderate(normal_user))
        
    def test_user_cannot_disable_group(self):
        normal_user, group = create_user(), create_group()
        self.assertFalse(group.can_disable(normal_user))
        
    def test_user_cannot_modify_group(self):
        normal_user, group = create_user(), create_group()
        self.assertFalse(group.can_modify(normal_user))
        
    def test_moderator_cannot_modify_group(self):
        normal_user, group = create_user(), create_group()
        group.moderators.add(normal_user)
        self.assertFalse(group.can_modify(normal_user))
        
    def test_staff_cannot_modify_group(self):
        staff_user, group = create_staff(), create_group()
        self.assertFalse(group.can_modify(staff_user))
        
    def test_founder_can_modify_group(self):
        normal_user, group = create_user(), create_group()
        group.founder = normal_user
        self.assertTrue(group.can_modify(normal_user))
        
    def test_founder_can_moderate_group(self):
        normal_user, group = create_user(), create_group()
        group.founder = normal_user
        self.assertTrue(group.can_moderate(normal_user))
        
    def test_moderator_can_moderate_group(self):
        normal_user, group = create_user(), create_group()
        group.moderators.add(normal_user)
        self.assertTrue(group.can_moderate(normal_user))
        
    def test_founder_cannot_disable_group(self):
        normal_user, group = create_user(), create_group()
        group.founder = normal_user
        self.assertFalse(group.can_disable(normal_user))
        
    def test_staff_cannot_moderate_group(self):
        staff_user, group = create_staff(), create_group()
        self.assertFalse(group.can_moderate(staff_user))
        
    def test_staff_can_disable_group(self):
        staff_user, group = create_staff(), create_group()
        self.assertTrue(group.can_disable(staff_user))

