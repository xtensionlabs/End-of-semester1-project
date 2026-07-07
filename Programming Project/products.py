"""
products.py
Stores and manages crop types
 used in the Agri-Tech Marketplace  .
"""

CROPS = [
    "Maize",
    "Beans",
    "Potatoes",
    "Tomatoes",
    "Onions",
    "Cabbage",
    "Carrots",
    "Rice",
    "Wheat",
    "Bananas"
]


def display_crops():
    """Display all available crops."""
    print("\nAvailable Crops:")
    for index, crop in enumerate(CROPS, start=1):
        print(f"{index}. {crop}")


def get_crop(choice):
    """Return crop name based on user's choice."""
    if 1 <= choice <= len(CROPS):
        return CROPS[choice - 1]
    return None

def crop_exists(crop_name):
    """Check if a crop exists in the list."""
    return crop_name.title() in CROPS

def add_crop(crop_name):
    """Add a new crop to the list if it doesn't already exist."""
    crop_name = crop_name.title()

    if crop_name not in CROPS:
        CROPS.append(crop_name)
        print(f"{crop_name} has been added to the list of crops.")
    else:
        print(f"{crop_name} already exists in the list of crops.")
    
def view_all_crops():
    """Return a list of all crops."""
    print("\nCurrent Crops:")
    for crop in sorted(CROPS):
        print(f"- {crop}")

if __name__ == "__main__":
    while True:
        print("\nCrop Management Menu:")
        print("1. View all crops")
        print("2. Add a new crop")
        print("3. Exit")

        choice = input("Enter your choice: ").strip()

        if choice == "1":
            view_all_crops()
        elif choice == "2":
            new_crop = input("Enter the name of the new crop: ").strip()
            add_crop(new_crop)
        elif choice == "3":
            print("Exiting Crop Management.")
            break
        else:
            print("Invalid choice. Please try again.")