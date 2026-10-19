export function grade(lesson,choice){return !!lesson?.quiz&&Number.isInteger(choice)&&choice===lesson.quiz.answer;}
export function loadReadings(storage,validIds){
  try{const data=JSON.parse(storage.getItem('prep.learning.v1'));return Array.isArray(data?.read)?[...new Set(data.read.filter(id=>validIds.includes(id)))]:[];}catch{return [];}
}
export function saveReadings(storage,ids){try{storage.setItem('prep.learning.v1',JSON.stringify({version:1,read:[...new Set(ids)]}));return true;}catch{return false;}}
