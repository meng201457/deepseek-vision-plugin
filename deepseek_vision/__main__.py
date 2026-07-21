from .client import (
    DeepSeekClient,
    BASE_URL,
    DEFAULT_HEADERS,
)

if __name__ == "__main__":
    import argparse
    import sys

    parser = argparse.ArgumentParser(description="DeepSeek Image Recognition")
    parser.add_argument("image", help="Path to image file")

    auth_group = parser.add_mutually_exclusive_group(required=True)
    auth_group.add_argument("-t", "--token", help="Auth token (from browser)")
    auth_group.add_argument(
        "-c",
        "--credentials",
        nargs=2,
        metavar=("PHONE", "PASSWORD"),
        help="Phone number and password",
    )

    parser.add_argument("-m", "--prompt", default="", help="Optional prompt")
    parser.add_argument("-s", "--stream", action="store_true", help="Stream output")
    parser.add_argument("-o", "--output", help="Output file path")

    args = parser.parse_args()

    if args.token:
        client = DeepSeekClient(token=args.token)
    else:
        client = DeepSeekClient(
            mobile=args.credentials[0], password=args.credentials[1]
        )

    try:
        if args.stream:
            result = client.recognize_image(args.image, args.prompt, stream=True)
            for chunk in result:
                print(chunk, end="", flush=True)
            print()
        else:
            result = client.recognize_image(args.image, args.prompt)
            print(result)

            if args.output:
                with open(args.output, "w", encoding="utf-8") as f:
                    f.write(result)
                print(f"Result saved to {args.output}")

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
