# Cloudinary Setup for Saree Images

## 1. Get Cloudinary Credentials

1. Sign up at [Cloudinary](https://cloudinary.com/)
2. Go to Dashboard
3. Copy your credentials:
   - Cloud Name
   - API Key
   - API Secret

## 2. Add to Environment Variables

Add to your `.env` file:

```env
CLOUDINARY_CLOUD_NAME=your_cloud_name
CLOUDINARY_API_KEY=your_api_key
CLOUDINARY_API_SECRET=your_api_secret
```

## 3. Install Dependencies

```bash
pip install cloudinary
```

## 4. Usage

### Upload Images
```bash
POST /api/sarees/upload-images
Content-Type: multipart/form-data
Authorization: Bearer <token>

files: [image1.jpg, image2.png]
```

### Response
```json
{
  "success": true,
  "message": "2 image(s) uploaded successfully",
  "data": {
    "urls": [
      "https://res.cloudinary.com/your-cloud/image/upload/v1234/sarees/abc123.jpg",
      "https://res.cloudinary.com/your-cloud/image/upload/v1234/sarees/def456.png"
    ]
  }
}
```

### Create Saree with Images
```json
POST /api/sarees
{
  "name": "Silk Saree",
  "selling_price": 5000,
  "images": [
    "https://res.cloudinary.com/your-cloud/image/upload/v1234/sarees/abc123.jpg",
    "https://res.cloudinary.com/your-cloud/image/upload/v1234/sarees/def456.png"
  ]
}
```

## Features
- **Automatic optimization**: Images are automatically optimized
- **Format conversion**: Auto-converts to best format (WebP when supported)
- **CDN delivery**: Fast global delivery via Cloudinary CDN
- **Transformations**: Can apply transformations on-the-fly

## File Restrictions
- **Allowed formats**: JPG, JPEG, PNG, WEBP
- **Max file size**: 5MB per image
- **Max files per upload**: 10 images
- **Storage folder**: `sarees/`
