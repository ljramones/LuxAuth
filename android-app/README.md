# Android Capture Client

Placeholder for the future Android capture client.

## Purpose

Kotlin/Jetpack Compose app that connects to a USB or Wi-Fi microscope, guides the
operator through a capture protocol, and uploads images to the auth-platform backend.

The backend is device-agnostic — microscope control belongs here, not in auth-platform.

## Backend APIs

| Endpoint | Service | Port |
|---|---|---|
| `POST /devices/register` | device-service | 8103 |
| `POST /devices/{id}/calibrations` | device-service | 8103 |
| `GET /capture-protocols` | capture-intake-service | 8106 |
| `POST /capture-sessions` | capture-intake-service | 8106 |
| `POST /capture-sessions/{id}/images` | capture-intake-service | 8106 |
| `GET /capture-sessions/{id}/status` | capture-intake-service | 8106 |
| `POST /capture-sessions/{id}/complete` | capture-intake-service | 8106 |
