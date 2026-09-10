import sys

def filter_spam(dialogues):
    # Dummy logic: removes exact duplicates
    return list({d["dialogue_id"]: d for d in dialogues}.values())

def filter_length(dialogues):
    # Dummy logic: keep dialogues with 2 to 8 replies
    return [d for d in dialogues if 2 <= len(d.get("replies", [1, 2])) <= 8]

if __name__ == "__main__":
    print("Clean module stub")
