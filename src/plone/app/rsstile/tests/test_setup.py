import unittest2 as unittest

from Products.CMFCore.utils import getToolByName

from plone.app.rsstile.testing import\
    PLONE_APP_RSSTILE_INTEGRATION


class TestExample(unittest.TestCase):

    layer = PLONE_APP_RSSTILE_INTEGRATION
    
    def setUp(self):
        self.app = self.layer['app']
        self.portal = self.layer['portal']
        self.qi_tool = getToolByName(self.portal, 'portal_quickinstaller')
    
    def test_product_is_installed(self):
        """ Validate that our products GS profile has been run and the product 
            installed
        """
        pid = 'plone.app.rsstile'
        installed = [p['id'] for p in self.qi_tool.listInstalledProducts()]
        self.assertTrue(pid in installed,
                        'package appears not to have been installed')
