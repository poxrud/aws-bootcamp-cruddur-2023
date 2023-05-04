require 'aws-sdk-s3'
require 'json'
require 'jwt'

def handler(event:, context:)
  puts "EVENT: #{event}"
 
  token = event['headers']['authorization'].split(' ')[1]
  puts({step: 'presignedurl', access_token: token}.to_json)

  body_hash = JSON.parse(event["body"])
  extension = body_hash["extension"]

  decoded_token = JWT.decode token, nil, false
  cognito_user_uuid = decoded_token[0]['sub']

  s3 = Aws::S3::Resource.new
  bucket_name = ENV["UPLOADS_BUCKET_NAME"]
  object_key = "#{cognito_user_uuid}.#{extension}"

  puts({object_key: object_key}.to_json)

  obj = s3.bucket(bucket_name).object(object_key)
  url = obj.presigned_url(:put, expires_in: 60 * 5)
  
  body = {url: url}.to_json
  { 
    headers: {
      "Access-Control-Allow-Headers": "*, Authorization",
      "Access-Control-Allow-Methods": "OPTIONS,PUT,POST"
    },
    statusCode: 200, 
    body: body 
  }
end # def handler