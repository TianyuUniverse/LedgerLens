"""Chinese presentation labels; stored identifiers and original user text stay intact."""
import csv
import io
import json
import re

CATEGORY_LABELS = {'Housing':'住房','Food':'餐饮','Transport':'交通','Shopping':'购物','Entertainment':'娱乐',
                   'Utilities':'生活缴费','Health':'医疗','Other':'其他','Education':'教育','Income':'收入','Transfer':'转账'}
CSV_HEADERS = {'date':'日期','description':'交易描述','amount':'金额','kind':'收支类型','category':'消费分类',
               'counterparty':'交易对方','note':'备注','source_kind':'原始类型','source_category':'原始分类'}
LABELS = {**CATEGORY_LABELS, 'expense':'支出','income':'收入','transfer':'转账','import':'导入标签','rule':'规则分类',
          'kind':'收支类型','human':'用户确认','memory':'分类记忆','model':'AI 建议','confirmed memory':'已确认记忆',
          'needs_review':'待确认','confirmed':'已确认','auto':'自动识别','balanced':'均衡调整','Balanced':'均衡调整',
          'shopping_first':'优先减少购物','Shopping first':'优先减少购物','less_food_change':'尽量保留餐饮预算',
          'Keep dining changes small':'尽量保留餐饮预算','grounded tools':'本地账单查询',
          'grounded tools (deterministic)':'本地账单查询（规则模式）','local tools · deterministic':'本地工具（规则模式）',
          'local clarification':'需要补充信息','local fallback · deterministic':'本地工具回退（规则模式）',
          'model tool calling · validated calculations':'AI 工具调用 · 金额已经程序校验',
          'edit':'修改账单','budget':'设置预算','plan':'保存自定义测算','confirm_purpose':'确认消费用途',
          'memory_update':'修改分类记忆','memory_delete':'删除分类记忆','generated_plan_save':'保存储蓄方案',
          'id':'编号','date':'日期','description':'交易描述','amount':'金额','amount_fen':'金额（分）','category':'消费分类',
          'counterparty':'交易对方','note':'备注','source_kind':'原始类型','source_category':'原始分类',
          'inserted_ids':'新增记录编号','duplicates':'跳过重复项','before':'修改前','after':'修改后','inputs':'输入条件',
          'result':'计算结果','changes':'修改内容','history_rewritten':'是否改写历史','memory_id':'记忆编号',
          'memory_version':'记忆版本','review_status':'审核状态','category_source':'分类来源','decision_reason':'分类依据',
          'revision':'记录版本','created_at':'创建时间','updated_at':'更新时间','fingerprint':'记录标识',
          'import_fingerprint':'原始导入标识','purpose':'实际用途','match':'匹配条件','example':'确认示例',
          'source_id':'来源账单编号','enabled':'是否启用','auto_apply':'是否自动复用','version':'版本',
          'target':'储蓄目标','current':'已有储蓄','months':'月数','cuts':'减支比例','locked':'固定开销类别',
          'floors':'最低预算','style':'方案类型','ledger_revision':'账单版本标识','saved':'是否已保存',
          'limit_fen':'预算上限','spent_fen':'已支出','overrun_fen':'超支金额','month':'月份',
          'target_fen':'目标金额','current_fen':'已有储蓄','required_monthly_fen':'每月所需储蓄',
          'baseline_monthly_fen':'基准每月储蓄','extra_required_fen':'还需增加的月储蓄','monthly_reduction_fen':'每月减少支出',
          'scenario_monthly_fen':'方案每月储蓄','projected_fen':'预计储蓄','gap_fen':'目标差额','feasible':'是否达到目标',
          'reductions':'减支明细','record_ids':'来源账单编号','assumption':'测算假设','monthly_amounts_fen':'每月类别预算',
          'monthly_cuts_fen':'每月类别减支','monthly_savings_fen':'每月可储蓄','constraints_passed':'限制条件已通过',
          'violations':'未满足条件','record_count':'账单笔数','exclude_ids':'本次排除编号','Monthly allowance':'每月生活费'}

for month,number in (('July',7),('August',8),('September',9)):
    for original,translated in (('Dorm rent','宿舍房租'),('Campus canteen','校园食堂'),('Grocery','日常采购'),
                                ('Metro','地铁交通'),('Taobao clothes','淘宝服饰'),('JD.com supplies','京东日用品'),
                                ('Cinema and games','电影与游戏'),('Phone bill and electric','话费与电费'),
                                ('Move between own accounts','本人账户互转')):
        LABELS[f'{original} {month}']=f'{number}月{translated}'

LABELS.update({'rent':'房租','housing':'住房','canteen':'食堂','restaurant':'餐饮','grocery':'日常采购','coffee':'咖啡',
               'lunch':'午餐','dinner':'晚餐','metro':'地铁','bus':'公交','taxi':'出租车','didi':'打车','taobao':'淘宝',
               'jd.com':'京东','clothes':'服饰','bookstore':'书店','cinema':'影院','movie':'电影','game':'游戏','concert':'演出',
               'electric':'电费','water bill':'水费','internet':'网络费','phone bill':'话费','hospital':'医院','pharmacy':'药店',
               'clinic':'门诊','tuition':'学费','course fee':'课程费','reason':'依据','confidence':'参考置信度','record_id':'账单编号'})
LABELS.update({'adventure_goal':'设立冒险目标','adventure_entry':'记录目标储蓄','adventure_archive':'调整目标归档',
               'adventure_reflect':'保存复盘心得','title':'目标名称','goal_id':'目标编号','deadline':'目标日期',
               'archived':'是否归档','deposit':'存入目标','withdraw':'从目标取回'})

MESSAGES = {
 'Unknown host.':'访问地址不受支持。', 'Route not found.':'未找到该页面或接口。',
 'Same-origin session token required. Refresh this page.':'页面会话已失效或来源不符，请刷新后重试。',
 'Use application/json.':'请使用 JSON 格式提交。', 'Request must be 1 byte to 2.2 MB.':'请求内容须大于 0 字节且不超过 2.2 MB。',
 'JSON body must be an object.':'提交内容必须为 JSON 对象。',
 'Database operation failed. No partial transaction saved. Please retry.':'数据库操作失败，本次修改未保存，请重试。',
 'Choose seed or followup synthetic sample.':'请选择第一步或第二步演示数据。',
 'Record ID must be an integer.':'账单编号必须为整数。', 'Record does not exist.':'未找到账单。',
 'Unknown tool argument.':'工具参数不受支持。', 'Tool is not approved.':'不允许调用该工具。',
 'Import records first.':'请先导入账单。', 'Import records before calculating a plan.':'请先导入账单，再计算方案。',
 'Excluded IDs must be a list of positive integers.':'排除编号必须为正整数列表。',
 'An excluded record does not exist in this analysis period.':'要排除的账单不在本次分析期间内。',
 'Choose an expense category.':'请选择有效的支出类别。', 'Choose a financial kind.':'请选择有效的收支类型。',
 'Description query must contain 1-300 characters.':'查询描述须为 1 至 300 个字符。',
 'Choose two different months.':'请选择两个不同的月份。', 'Months must be an integer from 1 to 60.':'月数须为 1 至 60 的整数。',
 'Locked categories must be distinct expense categories.':'固定开销必须为有效且不重复的支出类别。',
 'Unknown floor category.':'最低预算中包含无效类别。', 'Select a generated plan.':'请选择已生成的方案。',
 'Records changed since this preview. Generate and review the plans again.':'账单已发生变化，请重新生成并审核方案。',
 'Conversation ID must be a 32-character lowercase hexadecimal string.':'对话编号无效，请新建对话后重试。',
 'Question must contain 1-500 characters.':'问题须为 1 至 500 个字符。', 'use_model must be true or false.':'AI 开关必须为是或否。',
 'Several years are present. Specify months as YYYY-MM.':'账单包含多个年份，请明确月份，例如 2026-09。',
 'Plan arguments must be an object.':'方案参数必须为对象。',
 'Model changed the stated goal or horizon. Used local tools.':'AI 改动了既定目标或期限，已改用本地工具。',
 'Model omitted a fixed spending category. Used local tools.':'AI 遗漏了固定开销限制，已改用本地工具。',
 'Model omitted a minimum budget. Used local tools.':'AI 遗漏了最低预算，已改用本地工具。',
 'Choose one of the displayed candidate record IDs.':'请选择页面列出的候选账单编号。',
 'Exclude one source record at a time.':'请每次排除一笔账单。',
 'No model is configured.':'尚未配置 AI 模型。', 'Model did not finish within the round limit.':'AI 未在规定轮数内完成，已回退到本地工具。',
 'Model returned an invalid tool message.':'AI 返回的工具调用格式无效。',
 'Model final response did not match the evidence schema.':'AI 回答与账单依据格式不符。',
 'Model did not select a validated result.':'AI 未选择已校验的计算结果。', 'Model tool-call limit reached.':'AI 工具调用次数达到上限。',
 'Model returned invalid tool identifiers.':'AI 返回的工具编号无效。', 'Model returned invalid tool arguments.':'AI 返回的工具参数无效。',
 'Model tool response was invalid or unavailable.':'AI 工具响应无效或服务不可用，已回退到本地工具。',
 'Amount must be a decimal number.':'金额须为有效数字。',
 'Amount must be positive and no greater than RMB 100,000,000.':'金额须为正数且不超过 1 亿元；允许已有储蓄或预算为零。',
 'Amount must have at most two decimal places.':'金额最多保留两位小数。', 'Month must use YYYY-MM.':'月份格式须为“年-月”，例如 2026-09。',
 'Invalid month.':'月份无效。', 'Date must be a valid YYYY-MM-DD.':'日期无效，请使用“年-月-日”，例如 2026-09-01。',
 'Description must contain 1-300 characters.':'交易描述须为 1 至 300 个字符。',
 'Kind must be income, expense or transfer.':'收支类型须为收入、支出或转账。',
 'Category must agree with record kind.':'消费分类与收支类型不符。',
 'Unsupported memory fields.':'记忆中包含不支持的字段。', 'Memory category must agree with its financial kind.':'记忆分类与收支类型不符。',
 'Explain the confirmed purpose in 1-200 characters.':'请用 1 至 200 个字符说明实际用途。',
 'Choose a counterparty, description phrase or note phrase for the memory.':'请为记忆设置交易对方、描述片段或备注片段。',
 'Each matching condition must contain 2-300 characters.':'每项匹配条件须为 2 至 300 个字符。',
 'Automatic reuse needs a purpose phrase in the description or note. A payee or generic payment/transfer label alone is not enough.':'自动复用需要能区分用途的描述或备注，不能只凭收款方或“支付、转账”等通用标签。',
 'The memory conditions must match the confirmed example.':'记忆条件必须与本次确认的账单相符。',
 'Invalid confirmation request.':'确认信息无效。', 'remember must be true or false.':'是否记住用途须为是或否。',
 'Choose a memory and supported changes.':'请选择记忆并填写有效修改内容。', 'Memory ID must be an integer.':'记忆编号须为整数。',
 'This record changed. Refresh and review it again.':'账单已被修改，请刷新后重新审核。',
 'Choose the confirmed kind and category explicitly.':'请明确选择实际的收支类型和分类。',
 'Purpose must contain 1-200 characters.':'实际用途须为 1 至 200 个字符。', 'Memory does not exist.':'未找到该记忆。',
 'Unsupported memory change.':'不支持此项记忆修改。',
 'This correction would duplicate another record. Nothing was saved.':'此项修正会产生重复账单，本次未保存。',
 'Model endpoint redirected. Check its configured URL.':'AI 服务地址发生跳转，请检查配置。',
 'Configure an HTTPS model endpoint without embedded credentials.':'请使用 HTTPS 模型地址，不要在地址中写入密钥。',
 'Local provider configuration could not be read.':'无法读取本机 AI 配置。', 'Model response exceeded the size limit.':'AI 返回内容超过长度限制。',
 'Model connection failed or timed out.':'AI 连接失败或超时。', 'Model returned an invalid response.':'AI 返回内容无效。',
 'CSV must be UTF-8 and at most 2 MB.':'CSV 文件须为 UTF-8 编码，且不超过 2 MB。',
 'CSV requires distinct date, description, amount, kind headers. category is optional.':'CSV 表头须包含日期、交易描述、金额、收支类型，消费分类可选，且表头不能重复。',
 'CSV has no records.':'CSV 中没有账单。', 'Supply supported editable fields.':'请提供可修改的账单字段。',
 'Plan must be an object.':'方案格式无效。', 'Unknown reduction category.':'减支设置中包含无效类别。',
 'At most 5,000 records per import.':'每次最多导入 5000 笔账单。', 'Reductions must be between 0 and 100 percent.':'减支比例须在 0% 至 100% 之间。',
 'Column count does not match headers.':'该行列数与表头不符。', 'Reductions must be numbers.':'减支比例须为数字。',
 'Edit would duplicate another record. No changes saved.':'修改后会产生重复账单，本次未保存。',
 'Income record.':'此记录为收入。', 'Transfer excluded from income and spending.':'转账不计入收入和支出。',
 'No known keyword. Please review.':'没有识别到明确用途，请确认。', 'Manual correction':'用户手动修正',
 'User confirmed purpose.':'用户已确认用途。',
 'Known counterparty, but the confirmed context does not match.':'交易对方相同，但用途条件与已确认记忆不符。',
 'Imported category differs from a purpose signal. Confirm the actual use.':'原始分类与用途线索不一致，请确认实际用途。',
 'An institution payee alone does not establish education spending. Confirm the actual use.':'不能只因收款方是学校就计为教育支出，请确认实际用途。',
 'Memory requires review, conflicts with another memory, or has a different purpose signal.':'此记忆需审核、与其他记忆冲突，或当前账单出现了不同用途线索。',
 'Rules baseline. No language model is configured.':'当前使用本地规则，尚未配置 AI 模型。',
 'Model unavailable or returned invalid output. Used rules baseline.':'AI 服务不可用或返回格式无效，已改用本地规则。',
 'Context and confirmed memories supplied to the model. Review purpose and matching conditions before applying.':'AI 已参考账单上下文和确认记忆，请核对用途及适用条件后再应用。',
 'No records. Import data first.':'暂无账单，请先导入数据。',
 'Last 3 calendar months ending at latest imported month. Missing months count as zero. Data may be incomplete. Transfers excluded.':'统计范围为最新账单所在月及之前两个月。缺失月份按零计算，账单可能不完整；转账不计入收支。',
 'Imported records only. Transfers excluded. Missing months have no records, not proven zero real spending. Changes do not establish personal motivation.':'仅统计已导入的账单，不计转账。缺失月份表示未导入记录，不代表实际支出为零。支出变化不能单独说明消费动机。',
 'Three calendar-month mean, with missing months counted as zero. Income and category averages round to fen separately. Default reduction caps are proposal assumptions. Hard locks and minimums never relax. Future spending is not guaranteed.':'以最近三个日历月的均值测算，缺失月份按零计；收入和各类支出分别四舍五入到分。默认减支上限是方案假设，固定开销和最低预算不会自动放宽，未来结果不作保证。',
 'Repeated counterparty or description. Not proof of an unwanted subscription.':'发现跨月重复的交易对方或描述，尚不能据此认定是无用订阅。',
 'Only record patterns are reported. Ask the user before inferring motivation or cancelling a subscription.':'这里只报告账单规律。判断消费动机或取消订阅前，需要向用户确认。',
 ' Future income and spending repeat the 3-month mean. Category cuts are hypothetical. Rounding occurs per category to fen.':' 假设未来收支重复最近三个月均值，减支比例为情景设定，各类别金额分别四舍五入到分。'}


def label(value):
    return LABELS.get(value,value)


def translate(text):
    if not isinstance(text,str):
        return text
    if text in MESSAGES or text in LABELS:
        return MESSAGES.get(text,LABELS.get(text))
    if text.startswith('Import rejected. No records saved. '):
        parts=re.split(r'Row (\d+): ',text[len('Import rejected. No records saved. '):])
        return '导入已拒绝，未保存任何账单。'+''.join(f'第 {parts[i]} 行：{translate(parts[i+1].strip())} ' for i in range(1,len(parts)-1,2)).strip()
    if text.startswith('Last 3 calendar months'):
        return ''.join(MESSAGES.get(part,part) for part in (text.split(' Future income')[0], ' Future income'+text.split(' Future income',1)[1])) if ' Future income' in text else text
    match=re.fullmatch(r'Approved memory #(\d+) v(\d+): (.*)',text,re.S)
    if match:return f'已批准记忆 #{match[1]} · 第 {match[2]} 版：{match[3]}'
    match=re.fullmatch(r'Memory #(\d+) v(\d+): (.*)\. Review current purpose before applying\.',text,re.S)
    if match:return f'记忆 #{match[1]} · 第 {match[2]} 版：{match[3]}。应用前请确认本次用途。'
    if text.startswith('Matched keyword: '):return '匹配用途关键词：'+label(text[17:])
    match=re.fullmatch(r'(\w+) must be true or false\.',text)
    if match:return label(match[1])+'须为是或否。'
    match=re.fullmatch(r'(\w+) must be text with at most 300 characters\.',text)
    if match:return label(match[1])+'须为不超过 300 个字符的文本。'
    match=re.fullmatch(r'(\w+) is fixed below its requested minimum\. Change one of these conflicting limits\.',text)
    if match:return label(match[1])+'的固定金额低于最低预算，请先调整其中一项冲突条件。'
    if '(HTTP ' in text:
        code=re.search(r'HTTP (\d+)',text)
        meanings={'401':'API 密钥无效','402':'API 余额不足','429':'请求过于频繁','400':'AI 请求被拒绝','404':'未找到模型或接口'}
        return meanings.get(code[1],'AI 服务请求失败')+f'（状态码 {code[1]}）。' if code else 'AI 服务请求失败。'
    return text


def public_payload(value):
    """Translate system-generated presentation text, never user descriptions/purposes."""
    if isinstance(value,list):return [public_payload(item) for item in value]
    if not isinstance(value,dict):return value
    result={}
    for key,item in value.items():
        if key in ('error','notice','assumption','reason','decision_reason','source','label') and isinstance(item,str):
            item=translate(item)
            if key=='error' and item==value[key] and re.search('[A-Za-z]',item):
                item='操作未完成，请检查输入后重试。'
        elif key=='details' and isinstance(item,str):
            try:item=json.dumps(public_payload(json.loads(item)),ensure_ascii=False)
            except ValueError:pass
        else:item=public_payload(item)
        result[key]=item
    return result


def chinese_csv(rows, translate_examples=False):
    output=io.StringIO();writer=csv.writer(output);writer.writerow(CSV_HEADERS.values())
    for record in rows:
        values=[]
        for field in CSV_HEADERS:
            text=f"{record['amount_fen']/100:.2f}" if field=='amount' else str(record.get(field,''))
            if field in ('kind','category','source_kind','source_category') or (translate_examples and field=='description'):
                text=label(text)
            if text.startswith(('=','+','-','@','\t','\r')):text="'"+text
            values.append(text)
        writer.writerow(values)
    return output.getvalue().encode('utf-8-sig')
