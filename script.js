document.addEventListener('DOMContentLoaded', () => {
  // نسوي 250 confetti
  for(let i=0;i<250;i++){
    const confetti = document.createElement('div');
    confetti.classList.add('confetti');
    const randomX = Math.random() * 100 - 50;
    confetti.style.setProperty('--x', randomX);
    confetti.style.left = Math.random()*100 + 'vw';
    confetti.style.width = confetti.style.height = (Math.random()*12 + 5) + 'px';
    confetti.style.backgroundColor = `hsl(${Math.random()*360}, 100%, 50%)`;
    confetti.style.animationDuration = (Math.random()*3 + 2) + 's';
    document.body.appendChild(confetti);
  }

  // أصوات انفجارات، تشتغل بعد نقرة المستخدم
  const sounds = [
    "https://freesound.org/data/previews/341/341695_62445-lq.mp3",
    "https://freesound.org/data/previews/174/174027_3242494-lq.mp3"
  ];

  function playRandomSound(){
    const audio = new Audio(sounds[Math.floor(Math.random()*sounds.length)]);
    audio.volume = 0.3;
    audio.play();
  }

  // تشغيل الصوت بعد أول نقرة
  document.body.addEventListener('click', () => {
    playRandomSound();
  });
});
