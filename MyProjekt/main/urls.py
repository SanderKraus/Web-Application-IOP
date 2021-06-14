from django.urls import path

from . import views

urlpatterns = [
    path('', views.IndexView.as_view(), name='index'),
]


# CRUD-Aktionen Referenz-System
urlpatterns += [
    path('references', views.ReferenceList.as_view(), name='referencemodel-list'),
    path('reference/create/', views.ReferenceSystemCreate.as_view(),
         name='referencemodel-create'),
    path('reference/<int:pk>/', views.ReferenceDetail.as_view(),
         name='referencemodel-detail'),
    path('reference/<int:pk>/update/',
         views.ReferenceModelUpdate.as_view(), name='referencemodel-update'),
    path('reference/<int:pk>/delete/',
         views.ReferenceSystemDelete.as_view(), name='referencemodel-delete'),
]

# file upload
urlpatterns += [
    path('refupload/<int:pk>', views.ReferenceUpload.as_view(), name='refupload')
]

# CRUD-Aktionen Technologie
urlpatterns += [
    path('technologies/', views.TechnologyList.as_view(), name='technology-list'),
    path('technology/create/', views.TechnologyCreate.as_view(),
         name='technology-create'),
    path('technology/<int:pk>/', views.TechnologyDetail.as_view(),
         name='technology-detail'),
    path('technology/<int:pk>/update/',
         views.TechnologyUpdate.as_view(), name='technology-update'),
    path('technology/<int:pk>/delete/',
         views.TechnologyDelete.as_view(), name='technology-delete'),
]

# CRUD-Aktionen Tools
urlpatterns += [
    path('tool/<int:pk>/create', views.ToolCreate.as_view(),
         name='tool-create'),
    path('tool/<int:pk>/update',
         views.ToolUpdate.as_view(), name='tool-update'),
    path('tool/<int:pk>/delete/<int:technology_id>',
         views.ToolDelete.as_view(), name='tool-delete'),
]

# CRUD-Aktionen ToolAttributes
urlpatterns += [
    path('tool_attributes/<int:pk>/create', views.ToolAttributeCreate.as_view(),
         name='attr-create'),
    path('tool_attributes/<int:pk>/update',
         views.ToolAttributeUpdate.as_view(), name='attr-update'),
    path('tool_attributes/<int:pk>/delete/<int:technology_id>',
         views.ToolAttributeDelete.as_view(), name='attr-delete'),
]

# CRUD-Aktionen Technologiekette (Model: FctMembership)
urlpatterns += [
    path('reference/<int:pk>/update_technology',
         views.ReferenceModelTechnologyUpdate.as_view(), name='reference-technology'),
    path('reference/<int:pk>/delete_technology/<int:ref>',
         views.ReferenceModelTechnologyDelete.as_view(), name='reference-technology-delete')
]

# CRUD-Aktionen FctTabelle
urlpatterns += [
    path('fct_tabelle/<int:pk>/<int:merkmal>',
         views.FctTableForm.as_view(), name='fct-table')
]

# Redirect \ calculation fct_column volumes
urlpatterns += [
    path('fct_volume/<int:pk>',
         views.CalculateFctTableVolumes.as_view(), name='fct-volume'),

]

# Customer
urlpatterns += [
    path('items', views.CustomerItems.as_view(), name='item-list'),
    path('item/<int:pk>/', views.CustomerItem.as_view(), name='item-detail'),
    path('item/create', views.ItemUpload.as_view(), name='item-create'),
    path('item/<int:pk>/delete',
         views.CustomerItemDelete.as_view(), name='item-delete'),
    path('item/<int:pk>/<int:reference>',
         views.ItemFctBackwards.as_view(), name='item-fct'),
    path('item_compare/<int:pk>/<int:reference>',
         views.ItemComparison.as_view(), name='item-compare'),
    path('item_add/<int:pk>/<int:reference>',
         views.ItemAddFeatureToReference.as_view(), name='item-add')
]
