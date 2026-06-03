@echo off
echo [1/4] Reading Terraform outputs...
FOR /F "tokens=*" %%i IN ('terraform output -raw api_gateway_url')  DO SET API_URL=%%i
FOR /F "tokens=*" %%i IN ('terraform output -raw frontend_s3_bucket') DO SET BUCKET=%%i
FOR /F "tokens=*" %%i IN ('terraform output -raw cloudfront_url')    DO SET CF_URL=%%i

echo API URL    : %API_URL%
echo S3 Bucket  : %BUCKET%
echo CloudFront : %CF_URL%

echo.
echo [2/4] Writing config.js...
(
echo const CONFIG = {
echo   API_URL: "%API_URL%"
echo };
) > frontend\config.js

echo.
echo [3/4] Uploading frontend files to S3...
aws s3 sync frontend\ s3://%BUCKET%/ --profile AWS-Academy-Developer-726101441380 --delete

echo.
echo [4/4] Done! Open your app at: %CF_URL%
echo Note: CloudFront may take 2-5 min to propagate.