import pickle
from flask_admin.contrib import sqla
from flask_security import current_user
from flask import  url_for, redirect,  request, abort, Response
from flask_admin import BaseView, expose
from app import db
from app.database import RegisteredUser
from face_recognition.api import face_encodings
from utility.user_info_form import UserInfoForm
from utility.video_camera import VideoCamera
from const.consts import FACE_ID_ENCODING_SUCESS


# Create customized model view class
class MyModelView(sqla.ModelView):

    def is_accessible(self):
        if not current_user.is_active or not current_user.is_authenticated:
            return False

        if current_user.has_role('superuser'):
            return True

        return False

    def _handle_view(self, name, **kwargs):
        """
        Override builtin _handle_view in order to redirect users when a view is not accessible.
        """
        if not self.is_accessible():
            if current_user.is_authenticated:
                # permission denied
                abort(403)
            else:
                # login
                return redirect(url_for('security.login', next=request.url))


    # can_edit = True
    edit_modal = True
    create_modal = True    
    can_export = True
    can_view_details = True
    details_modal = True

class UserView(MyModelView):
    column_editable_list = ['email', 'first_name', 'last_name']
    column_searchable_list = column_editable_list
    column_exclude_list = ['password']
    column_details_exclude_list = column_exclude_list
    column_filters = column_editable_list

class ProductView(MyModelView):
    column_editable_list = ['product_name', 'product_unit_price', 'product_code', 'product_discount']
    column_searchable_list = column_editable_list
   
    column_filters = column_editable_list
    
class RegisteredUserView(MyModelView):
    column_editable_list = ['email', 'first_name', 'last_name', 'balance']
    column_exclude_list = ['face_encoding']
    column_details_exclude_list = column_exclude_list
    column_searchable_list = column_editable_list
    column_filters = column_editable_list


class CustomView(BaseView):
    @expose('/')
    def index(self):
        return self.render('admin/custom_index.html')

    def gen_check_identity_frame(self, camera):
        while True:
            frame = camera.check_identity()
            yield (b'--frame\r\n'
                b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n\r\n')

    @expose('/check_identity')
    def check_identity(self):
        return Response(self.gen_check_identity_frame(VideoCamera()),
                        mimetype='multipart/x-mixed-replace; boundary=frame') 

    def gen_face_encoding_frame(self, camera):
        while True:
            status ,face_encoding, frame_byte = camera.encode_face()
            yield (status, face_encoding, b'--frame\r\nContent-Type: image/jpeg\r\n\r\n' + frame_byte + b'\r\n\r\n')                     

    @expose('/encode_face')
    def encode_face(self):
        status, face_encoding, frame_bytes = next(self.gen_face_encoding_frame(VideoCamera()))
        if status == FACE_ID_ENCODING_SUCESS:
            global user_email
            user = db.session.query(RegisteredUser).filter(RegisteredUser.email == user_email).first()
            user.face_encoding = pickle.dumps(face_encoding)
            db.session.add(user)
            db.session.commit()
            return self.render("admin/encoding_success.html")
        else:
            return Response(frame_bytes, mimetype='multipart/x-mixed-replace; boundary=frame')   

user_email = None

class UserRegistrationView(BaseView):
    @expose('/', methods=['GET', 'POST'])
    def index(self):
        form = UserInfoForm(request.form)
        if request.method == 'POST' and form.validate():
            user = RegisteredUser()
            
            user.first_name = form.first_name.data
            user.last_name = form.last_name.data
            user.email = form.email.data
            global user_email
            user_email = form.email.data
            db.session.add(user)
            db.session.commit()
            
            # renew rank for every one:

            return self.render('admin/face_encoding.html')

        return self.render('admin/user_registration.html', form=UserInfoForm())