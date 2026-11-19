"""SCRUM-140: server-side idempotent copies preserve provenance across restart/edit."""
import unittest
import test_auth_api as auth
from test_suggested_recipes_api import SuggestedRecipesApiTest

class SaveSuggestionsApiTest(unittest.TestCase):
    client = auth.AuthApiTest.client
    request = auth.AuthApiTest.request
    register = auth.AuthApiTest.register
    start = SuggestedRecipesApiTest.start
    stop = SuggestedRecipesApiTest.stop
    setUp = SuggestedRecipesApiTest.setUp

    def test_copy_idempotence_edit_restart_and_isolation(self):
        a, b = self.client(), self.client()
        self.register(a, 'a@example.test'); self.register(b, 'b@example.test')
        original = self.request(a, '/api/recipes?filter=suggested')[1][0]
        path = '/api/recipes/' + original['id'] + '/save'
        status, saved, _ = self.request(a, path, 'POST', {'mealType':'Dinner'})
        self.assertEqual(status, 201)
        self.assertIsInstance(saved['id'], int)
        for field in ('name','ingredients','instructions','difficulty','prepTime'):
            self.assertEqual(saved[field], original[field])
        self.assertEqual(saved['suggestedId'], original['id'])
        self.assertEqual(saved['category'], original['plan'])
        self.assertEqual(self.request(a,path,'POST',{'mealType':'Lunch'})[:2], (200,saved))
        self.assertEqual(self.request(b,'/api/recipes')[1], [])
        self.assertEqual(self.request(a,'/api/recipes?filter=suggested')[1][0],original)
        edited={**auth.RECIPE,'name':'My edited copy'}
        self.assertEqual(self.request(a,'/api/recipes/'+str(saved['id']),'PUT',edited)[0],200)
        self.stop(); self.start()
        self.assertEqual(self.request(a,'/api/auth/login','POST',{'email':'a@example.test','password':auth.PASSWORD})[0],200)
        status, again, _ = self.request(a,path,'POST',{'mealType':'Dinner'})
        self.assertEqual(status,200); self.assertEqual(again['id'],saved['id'])
        self.assertEqual(again['name'],'My edited copy')
        self.assertEqual(len(self.request(a,'/api/recipes')[1]),1)
        self.assertEqual(again['suggestedId'],original['id'])

    def test_all_dietary_categories_and_balanced_fallback(self):
        a = self.client()
        self.register(a, 'a@example.test')
        for plan in ('High Protein', 'Low Calorie', 'Keto', 'Balanced'):
            self.stop()
            content = self.catalog.read_text(encoding='utf-8')
            import re
            self.catalog.write_text(re.sub(r'recipe.0.plan=.*', 'recipe.0.plan=' + plan, content), encoding='utf-8')
            self.start()
            self.request(a, '/api/auth/login', 'POST', {'email':'a@example.test','password':auth.PASSWORD})
            path = '/api/recipes/suggested:1/save'
            status, saved, _ = self.request(a, path, 'POST', {'mealType':'Dinner'})
            self.assertEqual(status, 201)
            self.assertEqual(saved['category'], 'My Recipes' if plan == 'Balanced' else plan)
            self.assertEqual(self.request(a, '/api/recipes?filter=saved')[1][0]['category'], saved['category'])
            self.assertEqual(self.request(a, path, 'POST', {'mealType':'Dinner'})[:2], (200, saved))
            self.request(a, '/api/recipes/' + str(saved['id']), 'DELETE')

    def test_validation_and_no_session(self):
        a=self.client();path='/api/recipes/suggested:1/save'
        self.assertEqual(self.request(a,path,'POST',{'mealType':'Dinner'})[0],401)
        self.register(a,'a@example.test')
        self.assertEqual(self.request(a,path,'POST',{'mealType':'Dinner'},verified=False)[0],403)
        for meal_type in ('','invalid'):
            self.assertEqual(self.request(a,path,'POST',{'mealType':meal_type})[0],400)
        self.assertEqual(self.request(a,'/api/recipes/suggested:999/save','POST',{'mealType':'Dinner'})[0],404)
        self.assertEqual(self.request(a,path)[0],405)
        self.assertEqual(self.request(a,'/api/recipes')[1],[])
