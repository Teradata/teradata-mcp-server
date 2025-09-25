#!/usr/bin/env python3
"""
Helper utility to generate Basic Auth tokens for MCP testing
"""

import argparse
import base64
import sys


def create_basic_auth_token(username: str, password: str) -> str:
    """Create a Base64 encoded Basic auth token from username and password."""
    credentials = f"{username}:{password}"
    encoded = base64.b64encode(credentials.encode('utf-8')).decode('ascii')
    return encoded


def decode_basic_auth_token(token: str) -> tuple[str, str]:
    """Decode a Base64 Basic auth token to username and password."""
    try:
        decoded = base64.b64decode(token).decode('utf-8')
        username, password = decoded.split(':', 1)
        return username, password
    except Exception as e:
        raise ValueError(f"Invalid token format: {e}")


def main():
    parser = argparse.ArgumentParser(description="MCP Basic Auth Token Helper")
    subparsers = parser.add_subparsers(dest='command', help='Available commands')

    # Encode command
    encode_parser = subparsers.add_parser('encode', help='Encode username:password to Base64')
    encode_parser.add_argument('username', help='Username')
    encode_parser.add_argument('password', help='Password')

    # Decode command
    decode_parser = subparsers.add_parser('decode', help='Decode Base64 token to username:password')
    decode_parser.add_argument('token', help='Base64 encoded token')

    args = parser.parse_args()

    if args.command == 'encode':
        token = create_basic_auth_token(args.username, args.password)
        print(f"Basic Auth Token: {token}")
        print(f"Authorization Header: Authorization: Basic {token}")
        print(f"Config JSON:")
        print(f'  "auth": {{')
        print(f'    "Authorization": "Basic {token}"')
        print(f'  }}')

    elif args.command == 'decode':
        try:
            username, password = decode_basic_auth_token(args.token)
            print(f"Username: {username}")
            print(f"Password: {password}")
        except ValueError as e:
            print(f"Error: {e}", file=sys.stderr)
            sys.exit(1)

    else:
        parser.print_help()


if __name__ == "__main__":
    main()