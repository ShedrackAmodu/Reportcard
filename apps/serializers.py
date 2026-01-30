from rest_framework import serializers

from .models import School, User, ClassSection, Subject, GradingScale, GradingPeriod, StudentEnrollment, Grade, Attendance, UserApplication, SchoolProfile, SupportTicket, ReportCard, ReportTemplate


class SchoolSerializer(serializers.ModelSerializer):
    class Meta:
        model = School
        fields = '__all__'


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = '__all__'
        extra_kwargs = {'password': {'write_only': True}}

    def create(self, validated_data):
        user = User.objects.create_user(**validated_data)
        return user


class ClassSectionSerializer(serializers.ModelSerializer):
    class Meta:
        model = ClassSection
        fields = '__all__'


class SubjectSerializer(serializers.ModelSerializer):
    class Meta:
        model = Subject
        fields = '__all__'


class GradingScaleSerializer(serializers.ModelSerializer):
    class Meta:
        model = GradingScale
        fields = '__all__'


class GradingPeriodSerializer(serializers.ModelSerializer):
    class Meta:
        model = GradingPeriod
        fields = '__all__'


class StudentEnrollmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = StudentEnrollment
        fields = '__all__'


class GradeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Grade
        fields = '__all__'


class AttendanceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Attendance
        fields = '__all__'


class UserApplicationSerializer(serializers.ModelSerializer):
    submitted_by_name = serializers.CharField(source='submitted_by.get_full_name', read_only=True)
    reviewed_by_name = serializers.CharField(source='reviewed_by.get_full_name', read_only=True)
    school_name = serializers.CharField(source='school.name', read_only=True)

    class Meta:
        model = UserApplication
        fields = '__all__'


class SchoolProfileSerializer(serializers.ModelSerializer):
    """Serializer for SchoolProfile model (white-label features)"""
    
    class Meta:
        model = SchoolProfile
        fields = '__all__'


class SupportTicketSerializer(serializers.ModelSerializer):
    """Serializer for SupportTicket model"""
    
    created_by_name = serializers.CharField(source='created_by.get_full_name', read_only=True)
    assigned_to_name = serializers.CharField(source='assigned_to.get_full_name', read_only=True)
    resolved_by_name = serializers.CharField(source='resolved_by.get_full_name', read_only=True)
    school_name = serializers.CharField(source='school.name', read_only=True)
    
    class Meta:
        model = SupportTicket
        fields = '__all__'


class ReportCardSerializer(serializers.ModelSerializer):
    """Serializer for ReportCard model"""
    
    student_name = serializers.CharField(source='student.get_full_name', read_only=True)
    student_username = serializers.CharField(source='student.username', read_only=True)
    grading_period_name = serializers.CharField(source='grading_period.name', read_only=True)
    template_name = serializers.CharField(source='template.name', read_only=True)
    school_name = serializers.CharField(source='school.name', read_only=True)
    published_by_name = serializers.CharField(source='published_by.get_full_name', read_only=True)
    
    class Meta:
        model = ReportCard
        fields = '__all__'
        read_only_fields = ['academic_year', 'average_grade', 'class_rank', 'published_at', 'generated_data', 'pdf_file', 'created_at', 'updated_at']
    
    def validate(self, attrs):
        """Validate report card data"""
        student = attrs.get('student')
        grading_period = attrs.get('grading_period')
        template = attrs.get('template')
        school = attrs.get('school')
        
        # Validate student exists and is a student role
        if student and student.role != 'student':
            raise serializers.ValidationError("Student must have 'student' role.")
        
        # Validate grading period belongs to school
        if grading_period and school and grading_period.school != school:
            raise serializers.ValidationError("Grading period must belong to the same school.")
        
        # Validate template belongs to school
        if template and school and template.school != school:
            raise serializers.ValidationError("Template must belong to the same school.")
        
        # Validate template is active
        if template and not template.is_active:
            raise serializers.ValidationError("Template must be active.")
        
        return attrs
    
    def create(self, validated_data):
        """Create a new report card"""
        # Auto-calculate academic year if not provided
        grading_period = validated_data.get('grading_period')
        if grading_period and not validated_data.get('academic_year'):
            validated_data['academic_year'] = f"{grading_period.start_date.year}/{grading_period.end_date.year}"
        
        # Auto-set school from student if not provided
        student = validated_data.get('student')
        if student and not validated_data.get('school'):
            validated_data['school'] = student.school
        
        return super().create(validated_data)
