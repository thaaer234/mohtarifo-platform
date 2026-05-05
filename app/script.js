const answers = Array.from(document.querySelectorAll(".answers button"));
const submitExam = document.querySelector("#submitExam");
const examFeedback = document.querySelector("#examFeedback");
const accuracyValue = document.querySelector("#accuracyValue");
const levelValue = document.querySelector("#levelValue");
const recommendationTitle = document.querySelector("#recommendationTitle");
const recommendationText = document.querySelector("#recommendationText");
const studyPlan = document.querySelector("#studyPlan");
const timer = document.querySelector("#timer");

let selectedAnswer = null;
let remainingSeconds = 598;

const planItems = [
  ["اليوم 1", "درس قصير", "قوانين النهايات + 12 سؤالًا"],
  ["اليوم 2", "تدريب موجه", "15 سؤال نهايات مركبة"],
  ["اليوم 3", "مراجعة أخطاء", "إعادة حل الأسئلة الخاطئة"],
  ["اليوم 4", "اختبار زمني", "نموذج 20 دقيقة"],
  ["اليوم 5", "تعزيز", "اشتقاق مرتبط بالنهايات"],
  ["اليوم 6", "محاكاة", "نموذج مؤتمت كامل"],
  ["اليوم 7", "قرار", "تقرير جاهزية وخطة لاحقة"],
];

function renderStudyPlan() {
  studyPlan.innerHTML = planItems
    .map(
      ([day, type, task]) => `
        <article class="day-card">
          <strong>${day}</strong>
          <span>${type}</span>
          <p>${task}</p>
        </article>
      `,
    )
    .join("");
}

function formatTime(seconds) {
  const minutes = Math.floor(seconds / 60).toString().padStart(2, "0");
  const rest = (seconds % 60).toString().padStart(2, "0");
  return `${minutes}:${rest}`;
}

function startTimer() {
  timer.textContent = formatTime(remainingSeconds);
  window.setInterval(() => {
    remainingSeconds = Math.max(0, remainingSeconds - 1);
    timer.textContent = formatTime(remainingSeconds);
  }, 1000);
}

answers.forEach((answer) => {
  answer.addEventListener("click", () => {
    answers.forEach((item) => item.classList.remove("selected"));
    answer.classList.add("selected");
    selectedAnswer = answer;
    examFeedback.textContent = "تم اختيار الإجابة. يمكنك اعتمادها الآن.";
  });
});

submitExam.addEventListener("click", () => {
  if (!selectedAnswer) {
    examFeedback.textContent = "اختر إجابة أولًا حتى يتم تصحيح المحاولة.";
    return;
  }

  const isCorrect = selectedAnswer.dataset.correct === "true";
  answers.forEach((answer) => {
    answer.classList.toggle("correct", answer.dataset.correct === "true");
    answer.classList.toggle("wrong", answer === selectedAnswer && !isCorrect);
  });

  if (isCorrect) {
    examFeedback.textContent = "إجابة صحيحة. ارتفعت الدقة المتوقعة إلى 78%.";
    accuracyValue.textContent = "78%";
    levelValue.textContent = "متقدم";
    recommendationTitle.textContent = "انتقل إلى اختبار زمني قصير";
    recommendationText.textContent =
      "الإجابة صحيحة، والخطوة الأفضل الآن اختبار بزمن محدود لقياس الثبات تحت الضغط.";
  } else {
    examFeedback.textContent = "الإجابة غير صحيحة. أضيفت المهارة إلى خطة المراجعة.";
    accuracyValue.textContent = "71%";
    levelValue.textContent = "متوسط";
    recommendationTitle.textContent = "راجع قانون جمع النهايات";
    recommendationText.textContent =
      "الخطأ مرتبط بتجميع القوانين الأساسية، لذلك تقترح المنصة درسًا قصيرًا ثم أسئلة مشابهة.";
  }
});

renderStudyPlan();
startTimer();
