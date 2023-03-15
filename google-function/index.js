const vision = require('@google-cloud/vision');
const Storage = require('@google-cloud/storage');
const Firestore = require('@google-cloud/firestore');
const client = new vision.ImageAnnotatorClient();


exports.helloGCS = async (event, context) => {
  console.log(`Event: ${JSON.stringify(event)}`);
  const filename = event.name;
  const filebucket = event.bucket;
  const fileLocation = event.metadata.location
  const fileDate = event.metadata.date
  const fileAuthor = event.metadata.name
  console.log(`New picture uploaded ${filename} in ${filebucket}`);
  const request = {
      image: { source: { imageUri: `gs://${filebucket}/${filename}` } },
      features: [
          { maxResults: 25,
            type: 'LABEL_DETECTION' },
          {
            maxResults: 25,
            type: 'OBJECT_LOCALIZATION'
          }
        ]
    };
  const [response] = await client.annotateImage(request);
  console.log(`Raw vision output for: ${filename}: ${JSON.stringify(response)}`);

  const labels = response.labelAnnotations.sort((ann1, ann2) => ann2.score - ann1.score).map(ann => ann.description)
  const objects = response.localizedObjectAnnotations.map((t)=>t.name)
  
  let property
  if(objects.filter((t)=>t.toLowerCase().includes('person')).length>0){
    property = 'People'
  }else if (objects.filter((t)=>t.toLowerCase().includes('flower')).length>0){
    property = 'Flowers'
  }else if (labels.filter((t)=>t.toLowerCase().includes('animal')).length>0){
    property = 'Animals'
  }else{
    property = 'Others'
  }
  console.log("property = " + property)
  const pictureStore = new Firestore().collection('pictures');
  const doc = pictureStore.doc(filename);
  await doc.set({
    filename: event.name,
    fileauthor: fileAuthor,
    filelocation: fileLocation,
    filedate: fileDate,
    filelocation: fileLocation,
    property: property,
    created: Firestore.Timestamp.now(),
    }, {merge: true});
  console.log("Stored metadata in Firestore");
};
