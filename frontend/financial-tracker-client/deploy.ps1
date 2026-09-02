npm run build
aws s3 sync dist/ s3://spendwithjot.com --delete
aws cloudfront create-invalidation --distribution-id E57LO3NE6RGNB --paths "/*"