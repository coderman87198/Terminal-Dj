from pydub import AudioSegment
import os

OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "finished_product")


def crossfade_tracks(files, crossfade_ms=3000, output_path="mix.mp3"):
    if not files:
        raise ValueError("No files provided to crossfade.")

    print("\nLoading first track...")
    final = AudioSegment.from_mp3(files[0])

    for f in files[1:]:
        print(f"Appending with crossfade: {f}")
        track = AudioSegment.from_mp3(f)
        final = final.append(track, crossfade=crossfade_ms)

    os.makedirs(OUTPUT_DIR, exist_ok=True)

    full_output_path = os.path.join(OUTPUT_DIR, os.path.basename(output_path))

    print(f"\nExporting final mix to: {full_output_path}")
    final.export(full_output_path, format="mp3")

    print("\nCleaning up original files...")
    for f in files:
        try:
            os.remove(f)
            print(f"Deleted: {f}")
        except Exception as e:
            print(f"Could not delete {f}: {e}")

    return full_output_path
