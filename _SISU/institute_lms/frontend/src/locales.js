export const locales=[
 ['en','English','English','gb'],['en-US','English (US)','English (US)','us'],['si','සිංහල','Sinhala','lk'],['ta','தமிழ்','Tamil','lk'],
 ['ar','العربية','Arabic (UAE)','ae'],['ar-SA','العربية (السعودية)','Arabic (Saudi Arabia)','sa'],['hi','हिन्दी','Hindi','in'],['ur','اردو','Urdu','pk'],
 ['fr','Français','French','fr'],['de','Deutsch','German','de'],['es','Español','Spanish','es'],['pt','Português','Portuguese','pt'],['pt-BR','Português (Brasil)','Portuguese (Brazil)','br'],
 ['it','Italiano','Italian','it'],['nl','Nederlands','Dutch','nl'],['tr','Türkçe','Turkish','tr'],['ru','Русский','Russian','ru'],['uk','Українська','Ukrainian','ua'],
 ['zh','简体中文','Chinese (Simplified)','cn'],['zh-TW','繁體中文','Chinese (Traditional)','tw'],['ja','日本語','Japanese','jp'],['ko','한국어','Korean','kr'],
 ['id','Bahasa Indonesia','Indonesian','id'],['ms','Bahasa Melayu','Malay','my'],['th','ไทย','Thai','th'],['vi','Tiếng Việt','Vietnamese','vn'],
 ['bn','বাংলা','Bengali','bd'],['ne','नेपाली','Nepali','np'],['fa','فارسی','Persian','ir'],['he','עברית','Hebrew','il'],
 ['pl','Polski','Polish','pl'],['sv','Svenska','Swedish','se'],['da','Dansk','Danish','dk'],['fi','Suomi','Finnish','fi'],['el','Ελληνικά','Greek','gr'],
 ['ro','Română','Romanian','ro'],['hu','Magyar','Hungarian','hu'],['cs','Čeština','Czech','cz'],['sw','Kiswahili','Swahili','ke'],['fil','Filipino','Filipino','ph']
].map(([code,native,title,country])=>({code,native,title,country}))
export const isRtl=code=>['ar','ur','fa','he','ps','sd','ug','yi','dv'].includes(code.split('-')[0])
export const flagPath=country=>(import.meta.env.DEV?'/flags/':'/assets/institute_lms/flags/')+country+'.svg'
