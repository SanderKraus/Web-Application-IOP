from django.contrib import admin

from .models import (CostReference, EcrCost, EcrFuzzy, FctAttribute, FctMembership, Feature, Technology, Tool,
                     ToolAttribute, Volume, ReferenceSystem, Item,
                     Halbzeug, FeatureAttribute, Result)

admin.site.register(
    [ReferenceSystem, Volume, ToolAttribute, FctMembership, FctAttribute,
     Item, Halbzeug, Feature, FeatureAttribute, Result, CostReference, EcrCost, Tool, Technology, EcrFuzzy])
