from plone.app.testing import PloneWithPackageLayer
from plone.app.testing import IntegrationTesting
from plone.app.testing import FunctionalTesting

import plone.app.rsstile


PLONE_APP_RSSTILE = PloneWithPackageLayer(
    zcml_package=plone.app.rsstile,
    zcml_filename='testing.zcml',
    gs_profile_id='plone.app.rsstile:testing',
    name="PLONE_APP_RSSTILE")

PLONE_APP_RSSTILE_INTEGRATION = IntegrationTesting(
    bases=(PLONE_APP_RSSTILE, ),
    name="PLONE_APP_RSSTILE_INTEGRATION")

PLONE_APP_RSSTILE_FUNCTIONAL = FunctionalTesting(
    bases=(PLONE_APP_RSSTILE, ),
    name="PLONE_APP_RSSTILE_FUNCTIONAL")
