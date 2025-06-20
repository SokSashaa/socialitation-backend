from django.http import JsonResponse
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import viewsets, filters, status
from rest_framework.decorators import action

from socialize_main.constants.roles import Roles
from socialize_main.models import Organization
from socialize_main.permissions.role_permission import RolePermission
from socialize_main.serializers.organizations import OrganizationSerializer


class OrganizationsView(viewsets.ModelViewSet):
    serializer_class = OrganizationSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    ordering = ['-pk']
    search_fields = ['name', 'site']
    ordering_fields = ['name', 'id']

    def get_permissions(self):
        return [RolePermission([Roles.ADMINISTRATOR.value])]

    def get_queryset(self):
        queryset = Organization.objects.all()
        return queryset

    @action(detail=False, methods=['POST'])
    def create_org(self, request):
        serializer = OrganizationSerializer(data=request.data)
        if not serializer.is_valid():
            return JsonResponse({'success': False, 'error': [serializer.errors]}, status=status.HTTP_400_BAD_REQUEST)
        else:
            organization, created = Organization.objects.get_or_create(
                name=serializer.data['name'],
                address=serializer.data['address'],
                phone_number=serializer.data['phone_number'],
                email=serializer.data['email'],
                site=serializer.data['site'],
            )
        if created:
            return JsonResponse({'success': True, 'result': OrganizationSerializer(organization).data},
                                status=status.HTTP_201_CREATED)
        else:
            return JsonResponse({'success': False, 'error': 'Организация уже существует'},
                                status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['DELETE'])
    def delete_org(self, request, pk):
        try:
            organization = Organization.objects.get(pk=pk)
            organization.delete()
            return JsonResponse({'success': True, 'result': 'Организация удалена'}, status=status.HTTP_200_OK)
        except Organization.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Организация не найдена'}, status=status.HTTP_404_NOT_FOUND)

    @action(detail=True, methods=['POST', 'PUT'])
    def update_org(self, request, pk):
        try:
            organization = Organization.objects.get(pk=pk)
            serializer = OrganizationSerializer(instance=organization, data=request.data)
            if not serializer.is_valid():
                return JsonResponse({'success': False, 'error': serializer.errors}, status=status.HTTP_400_BAD_REQUEST)

            serializer.save()

            return JsonResponse({'success': True, 'result': OrganizationSerializer(organization).data},
                                status=status.HTTP_200_OK)
        except Organization.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Организация не найдена'}, status=status.HTTP_404_NOT_FOUND)
