import json
import bcrypt
import base64
from django.db import IntegrityError
from .serializers import UserSerializer
from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from django.core.validators import RegexValidator
from django.http import HttpResponse
from django.http import JsonResponse
from .models import User

email = ""


def user(request):
    if request.method == 'POST':
        request_body = json.loads(request.body)
        if not request_body:
            return JsonResponse("No body Provided", status=204, safe=False)
        required_params = ['first_name', 'last_name', 'password', 'email_address']
        keys = request_body.keys()
        missing_keys = []
        for item in required_params:
            if item not in keys:
                missing_keys.append(item)
        if missing_keys:
            return HttpResponse("Missing {}".format(", ".join(missing_keys)), status=400, content_type="application/json")

        first_name = request_body['first_name']
        last_name = request_body['last_name']
        email = request_body['email_address']
        pwd = request_body['password']
        try:
            validate_email(email)
        except ValidationError:
            return HttpResponse("Invalid Email", status=400, content_type="application/json")
        try:
            validate = RegexValidator(regex='^(?=.*?[A-Z])(?=.*?[a-z])(?=.*?[0-9])(?=.*?[#?!@$%^&*-]).{8,}$')
            validate(pwd)
        except ValidationError:
            return HttpResponse("Enter a Strong Password", status=400, content_type="application/json")

        encrypt_pwd = encryptpwd(pwd)
        new_user = User(first_name=first_name, last_name=last_name, password=encrypt_pwd, email_address=email)
        ser = UserSerializer(new_user)
        try:
            new_user.save()
        except IntegrityError as e:
            return HttpResponse("User already exists", status=400, content_type="application/json")
        return JsonResponse(ser.data, status=201)
    else:
        return HttpResponse("Invalid Request method", status=400, content_type="application/json")


def get_user(request):
    pass


def update_user(request):
    if request.method == 'PUT':
        auth = request.headers.get('Authorization')
        auth_status = checkauth(auth)
        request_body = json.loads(request.body)
        if not request_body:
            return JsonResponse("No body Provided", status=204, safe=False)
        if auth_status == 'success':
            required_params = ['first_name', 'last_name', 'password', 'email_address']
            keys = request_body.keys()
            missing_keys = []
            for item in required_params:
                if item not in keys:
                    missing_keys.append(item)
            if missing_keys:
                return HttpResponse("Missing {}".format(", ".join(missing_keys)), status=400,
                                    content_type="application/json")

            user_obj = User.objects.get(email_address=email)
            changed = False
            for item in request_body.keys():
                if item == 'first_name' and user_obj.first_name != request_body['first_name']:
                    user_obj.first_name = request_body[item]
                    changed = True
                    continue
                elif item == 'last_name' and user_obj.last_name != request_body['last_name']:
                    user_obj.last_name = request_body['last_name']
                    changed = True
                    continue
                elif item == 'password' and not (decryptpwd(request_body['password'].encode('utf-8'), user_obj.password)):
                    encrypted_pwd = encryptpwd(request_body['password'])
                    user_obj.password = encrypted_pwd
                    changed = True
                    continue
                elif request_body['email_address'] != user_obj.email_address:
                    return HttpResponse("Email address cannot be updated", status=400)
            if changed:
                ser = UserSerializer(user_obj)
                user_obj.save()
                return JsonResponse(ser.data, status=200)
            else:
                return JsonResponse("No changes to update", status=200, safe=False)
        elif auth_status == "wrong_pwd":
            return JsonResponse("Wrong Password", status=403, safe=False)
        elif auth_status == "no_user":
            return JsonResponse("User Not Found", status=404, safe=False)

    elif request.method == 'GET':
        auth = request.headers.get('Authorization')
        auth_status = checkauth(auth)
        response = get_auth_status(auth_status)
        return response

    else:
        return JsonResponse("Invalid request method", status=400, safe=False)


def encryptpwd(pwd):
    salt = bcrypt.gensalt()
    encoded_pwd = pwd.encode('utf-8')
    hash_pwd = bcrypt.hashpw(encoded_pwd, salt).decode('utf-8')
    return hash_pwd


def decryptpwd(pwd, hashed_pwd):
    return bcrypt.checkpw(pwd, hashed_pwd.encode('utf-8'))


def checkauth(auth):
    global email
    encodedvalue = auth.split(" ")
    authvalue = encodedvalue[1]
    decoded_value = base64.b64decode(authvalue).decode('utf-8')
    creds = decoded_value.split(":")
    email = creds[0]
    pwd = creds[1]
    if (User.objects.filter(email_address=email).exists()):
        user_obj = User.objects.get(email_address=email)
        if (decryptpwd(pwd.encode('utf-8'),user_obj.password)):
            return "success"
        else:
            return "wrong_pwd"
    else:
        return "no_user"


def get_auth_status(auth_status):

    if auth_status == 'success':
        user_obj = User.objects.get(email_address=email)
        serialize = UserSerializer(user_obj)
        return JsonResponse(serialize.data, status=200)

    elif auth_status == 'wrong_pwd':
        return JsonResponse("Wrong Password", status=403, safe=False)

    elif auth_status == 'no_user':
        return JsonResponse("User Not Found", status=404, safe=False)
