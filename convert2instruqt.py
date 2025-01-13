import os
import subprocess
import shutil


def find_markdown_files(root_path):
    """Recursively find and return all markdown files, sorted by number following 'Lab_'."""
    markdown_files = []
    print(f"Searching for markdown files in: {os.path.abspath(root_path)}")
    for dirpath, _, filenames in os.walk(root_path):
        for file in filenames:
            if file.endswith(".md"):
                full_path = os.path.abspath(os.path.join(dirpath, file))
                markdown_files.append(full_path)

    # Sort files by numerical prefix after 'Lab_'
    def sort_key(file_path):
        base_name = os.path.basename(file_path)
        try:
            parts = base_name.split("_", 2)
            if parts[0].lower() == "lab":
                return int(parts[1])  # Extract the number after 'Lab_'
        except (IndexError, ValueError):
            pass
        return float("inf")  # Place non-matching files at the end

    markdown_files.sort(key=sort_key)
    print(f"Found markdown files: {markdown_files}")
    return markdown_files


def extract_title_from_filename(md_file_path):
    """Extract the challenge title by removing 'Lab' and numbers."""
    base_name = os.path.basename(md_file_path)
    parts = base_name.split("_", 2)
    if len(parts) > 2 and parts[0].lower() == "lab":
        title = parts[2].replace(".md", "").replace("_", " ").strip()
    else:
        title = base_name.replace(".md", "").replace("_", " ").strip()

    # Remove leading/trailing numbers and return the title
    return " ".join(word for word in title.split() if not word.isdigit()).capitalize()


def update_owner_in_track_yml(track_dir, team_slug):
    """Update the owner field in track.yml."""
    track_yml_path = os.path.join(track_dir, "track.yml")
    if not os.path.exists(track_yml_path):
        print(f"track.yml not found in {track_dir}. Skipping owner update.")
        return

    print(f"Updating owner field in {track_yml_path} to '{team_slug}'...")
    updated_lines = []
    with open(track_yml_path, "r") as file:
        for line in file:
            if line.strip().startswith("owner:"):
                updated_lines.append(f"owner: {team_slug}\n")
            else:
                updated_lines.append(line)

    with open(track_yml_path, "w") as file:
        file.writelines(updated_lines)
    print("Owner field updated successfully.")


def create_track_and_challenges(old_lab_path, new_track_title, template_slug, team_slug):
    """Create the track and challenges."""
    # Step 1: Find markdown files in the old structure
    markdown_files = find_markdown_files(old_lab_path)
    if not markdown_files:
        print(f"No markdown files found in {old_lab_path}. Aborting.")
        return

    # Step 2: Create the new track
    print(f"Creating new track: {new_track_title}")
    try:
        subprocess.run(
            ["instruqt", "track", "create", "--title", new_track_title, "--from", template_slug],
            check=True,
        )
    except subprocess.CalledProcessError as e:
        print(f"Error creating track '{new_track_title}': {e}")
        return

    # Navigate to the newly created track directory
    track_dir = os.path.abspath(new_track_title.lower().replace(" ", "-"))
    if not os.path.exists(track_dir):
        print(f"Track directory '{track_dir}' not found. Aborting.")
        return
    os.chdir(track_dir)

    # Step 3: Remove the untitled-challenge folder
    for folder in os.listdir("."):
        if folder.startswith("01-untitled-challenge"):
            print(f"Removing skeleton folder: {folder}")
            shutil.rmtree(folder)

    # Step 4: Update the owner in track.yml
    update_owner_in_track_yml(os.getcwd(), team_slug)

    # Step 5: Create challenges and append content for each markdown file
    for md_file in markdown_files:
        # Extract the challenge title from the markdown file
        challenge_title = extract_title_from_filename(md_file)
        print(f"Creating challenge: {challenge_title}")
        print(f"Original markdown file path: {md_file}")

        # Create the challenge using instruqt CLI
        try:
            subprocess.run(
                ["instruqt", "challenge", "create", "--title", challenge_title],
                check=True,
            )
        except subprocess.CalledProcessError as e:
            print(f"Error creating challenge '{challenge_title}': {e}")
            continue

        # Dynamically detect the newly created challenge directory
        challenge_dirs = sorted(
            [os.path.abspath(d) for d in os.listdir(".") if os.path.isdir(d)],
            key=os.path.getmtime,
            reverse=True,
        )
        if not challenge_dirs:
            print(f"No directories found after creating challenge '{challenge_title}'. Skipping append.")
            continue

        challenge_dir = challenge_dirs[0]
        assignment_path = os.path.join(challenge_dir, "assignment.md")
        print(f"Detected challenge directory: {challenge_dir}")
        print(f"Assignment path: {assignment_path}")

        # Append the old markdown content to the new assignment.md
        if os.path.exists(assignment_path):
            print(f"Appending content from {md_file} to {assignment_path}...")
            with open(md_file, "r") as old_md, open(assignment_path, "a") as new_md:
                new_md.write("\n\n")
                new_md.write(old_md.read())
            print(f"Appended content to {assignment_path}")
        else:
            print(f"assignment.md not found in {challenge_dir}. Skipping append.")

    # Step 6: Validate the track
    validate_track()


def validate_track():
    """Validate the Instruqt track structure."""
    try:
        print("Validating track...")
        subprocess.run(["instruqt", "track", "validate"], check=True)
        print("Track validated successfully.")
    except subprocess.CalledProcessError as e:
        print(f"Track validation failed: {e}")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Convert old lab environment format to Instruqt track format.")
    parser.add_argument("old_lab_path", help="Path to the old lab environment root directory")
    parser.add_argument("new_track_title", help="Title of the new Instruqt track")
    parser.add_argument("--template_slug", default="ntc/test-template", help="Template slug for Instruqt track")
    parser.add_argument("--team_slug", default="ntc", help="Team slug for Instruqt owner")

    args = parser.parse_args()
    create_track_and_challenges(args.old_lab_path, args.new_track_title, args.template_slug, args.team_slug)
