from rest_framework import serializers

from socialize_main.models import Organization

class OrganizationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Organization
        fields = ['id','name','site','address','email','phone_number']
        read_only_fields = ['id']

    def update(self, instance, validated_data):
        instance.name = validated_data.get("name", instance.name)
        instance.email = validated_data.get("email", instance.email)
        instance.address = validated_data.get("address", instance.address)
        instance.site = validated_data.get("site", instance.site)
        instance.phone_number = validated_data.get("phone_number", instance.phone_number)
        instance.save()
        return instance

class CompactOrganizationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Organization
        fields = ['id','name']