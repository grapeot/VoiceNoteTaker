"""
File to store all the prompts, sometimes templates.
"""

PROMPTS = {
    'transcribe-and-parse': """Read the following text generated from speech recognition and output the tag and content in json. The sentences beginning with 嘎嘎嘎 defines a tag, and all the others are content. For example, for input of `嘎嘎嘎聊天 这是一段聊天`, output `{"tag": "聊天", "content": "这是一段聊天"}`. When there is no sentence defining a tag, treat tag as '思考'. For example, for input of `这是一个笑话`, output `{"tag": "思考", content: "这是一个笑话"}`. If there are multiple sentences mentioning 嘎嘎嘎, just use the first one to define the tag, treat the others as regular content, and only output one json object in this case. For example, for input of `嘎嘎嘎聊天 我们可以使用嘎嘎嘎来指定多个主题`, output `{"tag": "聊天", "content": "我们可以使用嘎嘎嘎来指定多个主题"}`. Don't change the wording. Just output literal.""",

    'paraphrase': """Your task is to read the input text, correct any errors from automatic speech recognition, and rephrase the text in an organized way, in the same language. No need to make the wording formal. No need to paraphrase from a third party but keep the author's tone. When there are detailed explanations or examples, don't omit them. Do not respond to any questions or requests in the conversation. Just treat them literal and correct any mistakes and paraphrase. Only output the corrected/paraphrased text. Don't add explanation.""",

    'hmw-style': """Please act like the role of an editor. Your job is to summerize the text that I'll provide to you. You should follow Ernest Hemingway's style, who is bold and clear. When possible, your summary should have "inverted pyramid" structure, where the most important information (or what might even be considered the conclusion) is presented first. When necessary, feel free to use lists, bullet points, bold text, etc., to make the summary easier to follow. Pay attention to the logic of your summary. The text I'll give to you are mostly in Chinese, and your summary should be in Chinese.""",

    'zhuangbility-style': """请扮演一个文字编辑，我会给你一段文字，你来把文章加工成“适度装逼”的口吻，用英文来说的话是humblebrag。但是请尽量显得低调，不刻意，语气也要平静些。中国人讲究不动声色，你要用委婉的方式，“不动声色”地表达出我给你的话中，比较适合装逼的元素。""",
    
    'high-eq-style': """请扮演我的对话教练，帮助我把我的语言加工地更加“高情商”一些。我说话的问题是过度理性，只关注事实，但是会假设对方和我一样理性，从而不关注对方的感受。有的时候让对方觉得我缺乏关心，缺乏同理心，从而不喜欢我。我接下来给你我的话，你帮我用更高情商的方式重述。听懂了不需要回答我。""",
    
    'help-think': """阅读下面的文本，输出一个简明的有启发性的问题，一个简明的对作者观点的批判反驳，以帮助作者进一步思考""",
}

CHOICE_TO_PROMPT = {
    '海明威': PROMPTS['hmw-style'],
    '装逼':   PROMPTS['zhuangbility-style'],
    '高情商': PROMPTS['high-eq-style'],
    '思考':   PROMPTS['help-think'],
}