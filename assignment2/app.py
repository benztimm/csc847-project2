from flask import Flask, render_template, request, redirect, url_for, jsonify
from google.cloud import storage, firestore
from google.oauth2 import service_account
from werkzeug.utils import secure_filename
import mimetypes
import asyncio
import time


ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
client = storage.Client()
bucket = client.get_bucket("uploaded-picture-csc847-asmt2")
db = firestore.Client()
app = Flask(__name__)


@app.route("/upload")
def index():
    return render_template("upload.html",status = '')


@app.route("/")
def gallery():
    docs = db.collection('pictures').order_by(
        "created", direction=firestore.Query.DESCENDING).stream()
    images = []
    for doc in docs:
        document = doc.to_dict()
        images.append(document)
    return render_template("gallery.html", images=images, header="PhotoBook")


@app.route("/gallery/<category>")
def category(category):
    print(category)
    if category!='Animals' and category !='People' and category != 'Flowers':
        docs = db.collection('pictures').where('property', 'not-in', ["Animals","People","Flowers"]).order_by('property').order_by(
        'created', direction=firestore.Query.DESCENDING).stream()
    else:
        docs = db.collection('pictures').where('property', '==', category).order_by(
        'created', direction=firestore.Query.DESCENDING).stream()
    images = []
    for doc in docs:
        document = doc.to_dict()
        images.append(document)
    return render_template("gallery.html", images=images, header=category)


@app.route('/images/<image_name>')
def serve_image(image_name):
    blob = bucket.blob(image_name)
    image = blob.download_as_bytes()
    return image, {'Content-Type': blob.content_type}


@app.route("/edit-image/<image_name>", methods=["GET", "POST"])
def edit(image_name):
    if request.method == 'POST':
        doc = db.collection('pictures').document(image_name)
        file = request.files["file"]
        if file and allowed_file(file.filename):
            # get info from olddoc
            olddoc = doc.get().to_dict()
            # upload new photo
            filename = secure_filename(file.filename)
            content_type = mimetypes.guess_type(filename)[0]
            blob = bucket.blob(file.filename)
            blob.metadata = {
                "name": olddoc['fileauthor'],
                "location": olddoc['filelocation'],
                "date": olddoc['filedate']
            }
            blob.upload_from_file(file, content_type=content_type)
            time.sleep(4)

            # by now firestore should get the new doc already
            newdoc = db.collection('pictures').document(file.filename)
            if newdoc.get().exists:
                # update newdoc with old document change only file name
                # leave category "property" to Vision API to decide
                newdoc.update({'created': olddoc['created']})
                newdoc.update({'fileauthor': olddoc['fileauthor']})
                newdoc.update({'filedate': olddoc['filedate']})
                newdoc.update({'filelocation': olddoc['filelocation']})
                newdoc.update({'filename': file.filename})
                # delete old photo from GCS
                blob = bucket.blob(olddoc['filename'])
                blob.delete()
                # delete old doc from firestore
                doc.delete()
                # set current doc to be new doc
                doc = newdoc

        if request.form['fileauthor']:
            doc.update({'fileauthor': request.form['fileauthor']})
        if request.form['filelocation']:
            doc.update({'filelocation': request.form['filelocation']})
        if request.form['filedate']:
            doc.update({'filedate': request.form['filedate']})
        if request.form['property']:
            doc.update({'property': request.form['property']})

        metadata = doc.get().to_dict()
        images = metadata['filename']
        return render_template("image.html", images=images, metadata=metadata)
    else:
        doc_ref = db.collection('pictures').document(image_name)
        metadata = doc_ref.get().to_dict()
        images = metadata['filename']
        return render_template("image.html", images=images, metadata=metadata)


@app.route("/upload", methods=["POST"])
def upload():
    file = request.files["file"]
    name = request.form['name']
    location = request.form['location']
    date = request.form['date']
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        content_type = mimetypes.guess_type(filename)[0]
        blob = bucket.blob(file.filename)
        blob.metadata = {
            "name": name,
            "location": location,
            "date": date
        }

        blob.upload_from_file(file, content_type=content_type)
        time.sleep(4)
        return redirect(url_for("gallery"))
    else:
        status = f'Invalid filetype. Allowed extensions: {", ".join(ALLOWED_EXTENSIONS)}'
        return render_template('upload.html',status=status)


def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


@app.route("/delete/<image_name>/<page>", methods=["POST"])
def delete(image_name,page):
    doc = db.collection('pictures').document(image_name)
    doc.delete()
    blob = bucket.blob(image_name)
    blob.delete()
    return redirect(url_for("category",category=page))


@app.route('/get-documents/')
def get_documents():
    docs = db.collection('pictures').document(
        'astronomy-1867616__480.jpg').get()
    if docs.exists:
        return 'exist'
    else:
        return 'not exist'


if __name__ == "__main__":
    app.run(debug=True)
