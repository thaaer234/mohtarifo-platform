import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from accounts.models import StudentProfile

def guess_gender_from_name(full_name):
    if not full_name:
        return 'unknown'
    
    parts = full_name.strip().split()
    if not parts:
        return 'unknown'
        
    # Normalize name string
    first_name = parts[0].replace('أ', 'ا').replace('إ', 'ا').replace('آ', 'ا').replace('ة', 'ه')
    
    # Common Levant/Syrian Female Names (Extremely frequent)
    female_names = {
        "شام", "حلا", "لين", "رهف", "رغد", "شهد", "غلا", "نور", "مريم", "رؤى", "ريم", "تسنيم", "فاطمه",
        "بتول", "تالا", "ماسه", "مياس", "جودي", "مرح", "جنى", "ريتاج", "فرح", "روان", "علا", "غنى", "سيدرا", 
        "سدره", "هبه", "منى", "ياسمين", "راما", "رشا", "مرام", "رند", "نادين", "لارا", "هديل", "ولاء", "لميس",
        "نورال", "سلام", "اريج", "وئام", "بيان", "شيرين", "خلود", "شروق", "سجى", "سحر", "سما", "رنا", "هاله",
        "مي", "ميرنا", "لجين", "جيهان", "غدير", "عبير", "فاتن", "ناديا", "نجوى", "نهى", "نورالهدى", "شوق"
    }
    
    if first_name in female_names:
        return 'female'
        
    # Common Male exceptions that end with typical female endings (ه, ى, ا)
    male_exceptions = {
        "علاء", "بهاء", "ضياء", "حمزه", "عبيده", "قتيبه", "طلحه", "اسامه", "حذيفه", "عروه", "زكريا", 
        "يحيى", "مصطفى", "موسى", "عيسى", "طه", "رضا", "مرتضى"
    }
    if first_name in male_exceptions:
        return 'male'
        
    # Ending patterns
    if first_name.endswith('ه'):  # normalized 'ة'
        return 'female'
    if first_name.endswith('ى'):
        return 'female'
    if first_name.endswith('اء') and not first_name.endswith('لاء') and not first_name.endswith('هاء'): 
        # Filters out علاء، بهاء، ضياء while capturing لمياء، شيماء
        return 'female'
        
    return 'male'

profiles = StudentProfile.objects.all().select_related('user')
updated_count = 0
male_count = 0
female_count = 0

for p in profiles:
    full_name = p.user.get_full_name() or p.user.username
    guessed = guess_gender_from_name(full_name)
    
    # Update the profile
    p.gender = guessed
    p.save()
    
    updated_count += 1
    if guessed == 'male':
        male_count += 1
    else:
        female_count += 1

print(f"Completed Gender Auto-Prediction Process!")
print(f"Total Analyzed Students: {updated_count}")
print(f"Guessed Males: {male_count}")
print(f"Guessed Females: {female_count}")
