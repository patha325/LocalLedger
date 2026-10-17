from pathlib import Path
import csv,io,json,hashlib
import pandas as pd
import plotly.express as px
import streamlit as st
from finance import Ledger,CATEGORIES,money
import ai
from importing import read_table, sheet_names, suggest_columns, mapped_csv

st.set_page_config(page_title='LocalLedger',page_icon='◉',layout='wide')
st.markdown('''<style>.stApp{background:#f5f7fb}h1,h2,h3{color:#162b4d}div[data-testid="stMetric"]{background:white;padding:20px;border-radius:14px;border:1px solid #e5eaf2}</style>''',unsafe_allow_html=True)
DATA=Path(__file__).parent/'data';DATA.mkdir(exist_ok=True);(DATA/'documents').mkdir(exist_ok=True)
ledger=Ledger(DATA/'ledger.sqlite3')
st.title('LocalLedger')
st.caption('Your household, in one view · Local records · Verified totals')
accounts=ledger.accounts()
with st.sidebar:
    st.header('View')
    currency=st.selectbox('Currency',['SEK','EUR','GBP','USD'])
    owners=sorted({a['owner'] for a in accounts})
    selected=st.multiselect('People',owners,default=owners)
    model=st.text_input('Local Ollama model','qwen3:8b')
    st.caption('Currencies are reported separately. Internal household transfers remain excluded in person views.')
    if st.button('Load demonstration household',disabled=bool(accounts)):
        for name,owner in [('Current account','Alex'),('Savings','Alex'),('Partner account','Sam')]:ledger.add_account(name,owner,'SEK')
        for a in sorted(ledger.accounts(), key=lambda a: a["id"]):
            p=Path(__file__).parent/'examples'/f"{a['id']}.csv"
            ledger.import_csv(p.read_text(),a['id'],'date','description','amount')
        ledger.link(3,6);ledger.link(4,9)
        for r in ledger.rows():
            if r['description']=='Salary':ledger.categorise(r['id'],'Salary')
            if 'Groceries' in r['description']:ledger.categorise(r['id'],'Groceries')
        st.rerun()

tabs=st.tabs(['Overview','Accounts & import','Transactions','Transfers','Ask & documents'])
with tabs[0]:
    summary=ledger.summary(currency,selected)
    months=summary['months']
    month=st.selectbox('Month',['All months']+[r['month'] for r in months])
    shown=months if month=='All months' else [r for r in months if r['month']==month]
    cols=st.columns(3)
    for col,label,key in zip(cols,['Income','Expenses','Net cash flow'],['income','expenses','net']):col.metric(label,f"{sum(r[key] for r in shown)/100:,.2f} {currency}")
    st.caption('Based on imported records. Net cash flow is income minus expenses; it is not account balance or net worth. Confirmed internal transfers are excluded.')
    if months:
        df=pd.DataFrame(months);df[['income','expenses','net']]=df[['income','expenses','net']]/100
        st.plotly_chart(px.bar(df,x='month',y=['income','expenses'],barmode='group',color_discrete_sequence=['#18a999','#596cdd']),use_container_width=True)
        rows=[r for r in ledger.rows() if r['currency']==currency and r['owner'] in selected and not r['transfer'] and (month=='All months' or r['day'].startswith(month)) and (r['amount']<0 or r['category']=='Refund')]
        cats={}
        for r in rows:cats[r['category']]=cats.get(r['category'],0)-r['amount']/100
        if cats:st.plotly_chart(px.bar(x=list(cats.values()),y=list(cats),orientation='h',labels={'x':f'Net expenses ({currency})','y':'Category'}),use_container_width=True)
        st.download_button('Export summary',df.to_csv(index=False),'monthly-summary.csv','text/csv')
    else:st.info('Add accounts and import records, or load the demonstration household.')
with tabs[1]:
    with st.form('account'):
        st.subheader('Add an account')
        name=st.text_input('Account name');owner=st.text_input('Person / owner');cur=st.selectbox('Account currency',['SEK','EUR','GBP','USD']);opening=st.text_input('Opening balance before earliest imported transaction','0.00')
        if st.form_submit_button('Create account'):
            try:ledger.add_account(name,owner,cur,money(opening,'.'));st.rerun()
            except Exception as e:st.error(str(e))
    balances=ledger.balances()
    if balances:
        st.dataframe(pd.DataFrame([{**a,'opening':a['opening']/100,'balance':a['balance']/100} for a in balances]),hide_index=True)
        account=st.selectbox('Import into account',accounts,format_func=lambda a:f"{a['name']} · {a['owner']}")
        upload=st.file_uploader('Bank export',type=['csv','xls','xlsx'])
        if upload:
            try:
                payload=upload.getvalue();excel=upload.name.lower().endswith(('.xls','.xlsx'))
                header=int(st.number_input('Header row (1-based)',min_value=1,value=1))-1
                sheet=st.selectbox('Worksheet',sheet_names(payload,upload.name)) if excel else 0
                delim=',';encoding='utf-8-sig'
                if not excel:
                    delim=st.selectbox('CSV separator',[',',';','\t'])
                    encoding=st.selectbox('CSV encoding',['utf-8-sig','cp1252'])
                frame=read_table(payload,upload.name,header,sheet,delim,encoding)
                st.write('Source preview');st.dataframe(frame.head(10),hide_index=True)
                hints=suggest_columns(frame.columns);fields=['— Select —']+list(frame.columns)
                st.caption('Local header suggestions recognise common Swedish, English, German, French and Spanish names. Review every mapping. Unrecognised or ambiguous headers require manual selection.')
                split=st.checkbox('Separate debit and credit columns',value=bool(hints['debit'] and hints['credit'] and not hints['amount']))
                mapping={}
                for role,label in [('date','Date'),('description','Description')]+([('debit','Debit / outgoing'),('credit','Credit / incoming')] if split else [('amount','Signed amount')])+[('id','Bank transaction ID (optional)')]:
                    choice=st.selectbox(label+' column',fields,index=fields.index(hints[role]) if hints[role] else 0,key=f'map-{upload.name}-{header}-{sheet}-{role}')
                    mapping[role]=None if choice==fields[0] else choice
                fmt=st.selectbox('Text date format',['%Y-%m-%d','%d/%m/%Y','%m/%d/%Y','%d.%m.%Y','%Y%m%d','%d-%m-%Y'])
                dec=st.selectbox('Decimal separator in text amounts',['.',','])
                reverse=st.checkbox('Reverse amount signs (export uses positive for spending)')
                st.caption('Native Excel dates and numeric cells retain their types. Text dates and amounts use the settings above. Debit/credit values use their magnitudes. Totals and balance rows must be removed from the source before import.')
                try:
                    canonical,preview=mapped_csv(frame,mapping,fmt,dec,split,reverse)
                    st.write('Transactions to import');st.dataframe(preview.head(20),hide_index=True)
                    st.caption(f'{len(preview)} transactions. Positive = incoming; negative = outgoing. Existing duplicate detection and transfer review still apply.')
                    approved=st.checkbox('I have checked the mapping, dates, and amount signs',key='approve-'+hashlib.sha256((str(account['id'])+canonical).encode()).hexdigest())
                    if st.button('Import records',disabled=not approved):
                        result=ledger.import_csv(canonical,account['id'],'date','description','amount',id_col='id' if mapping.get('id') else None)
                        st.session_state['import_result']=result;st.rerun()
                except ValueError as e:st.info(str(e))
            except Exception as e:st.error(f'Could not read export: {e}')
        if 'import_result' in st.session_state:st.success(st.session_state.pop('import_result'))

with tabs[2]:
    rows=ledger.rows()
    if rows:
        st.dataframe(pd.DataFrame([{**r,'amount':r['amount']/100} for r in rows]),hide_index=True)
        r=st.selectbox('Transaction to categorise',rows,format_func=lambda r:f"#{r['id']} · {r['day']} · {r['description']} · {r['amount']/100:.2f} {r['currency']}")
        category=st.selectbox('Category',CATEGORIES,index=CATEGORIES.index(r['category']));remember=st.checkbox('Remember category for this exact merchant description')
        if st.button('Save category'):ledger.categorise(r['id'],category,remember);st.rerun()
        if st.button('Suggest with local LLM'):
            try:
                with st.spinner('Analysing locally…'):s=ai.suggest(r['description'],model)
                st.info(f'{s.category}: {s.reason}');st.caption('Select the suggestion above and save to apply it.')
            except Exception as e:st.error(f'Local model unavailable or invalid response: {e}')
with tabs[3]:
    st.subheader('Review internal transfers')
    st.write('Confirm movements between your included household accounts, including credit-card repayments. Matching amounts alone do not establish a transfer.')
    candidates=ledger.candidates()
    for a,b in candidates:
        with st.container(border=True):
            st.write(f"#{a['id']} {a['day']} {a['name']} → #{b['id']} {b['day']} {b['name']} · {b['amount']/100:.2f} {a['currency']}")
            st.caption(a['description']+' / '+b['description'])
            if st.button('Confirm transfer',key=f"pair{a['id']}-{b['id']}"):ledger.link(a['id'],b['id']);st.rerun()
    rows=ledger.rows()
    if rows:
        st.subheader('Match manually (including different booking months)')
        debits=[r for r in rows if r['amount']<0 and not r['transfer']];credits=[r for r in rows if r['amount']>0 and not r['transfer']]
        if debits and credits:
            label=lambda r:f"#{r['id']} {r['day']} {r['name']} {r['description']} {r['amount']/100:.2f} {r['currency']}"
            a=st.selectbox('Outgoing transaction',debits,format_func=label);b=st.selectbox('Incoming transaction',credits,format_func=label)
            if st.button('Link selected transactions'):
                try:ledger.link(a['id'],b['id']);st.rerun()
                except Exception as e:st.error(str(e))
    for tid in sorted({r['transfer'] for r in rows if r['transfer']}):
        st.write('Confirmed transfer',tid)
        if st.button('Undo',key=f'undo{tid}'):ledger.unlink(tid);st.rerun()
    st.caption('Unmatched movements remain in income/expenses until confirmed. Different currencies or transfer fees require separate review; automatic FX matching is not supported.')
with tabs[4]:
    q=st.text_input('Question about the selected household view','Explain the monthly income and expense trends.')
    if st.button('Explain verified summary'):
        try:
            context={'currency':currency,'people':selected,**ledger.summary(currency,selected)}
            with st.spinner('Analysing locally…'):answer=ai.explain(q,context,model)
            st.write(answer)
            with st.expander('Verified figures and source transaction IDs'):st.json(context)
        except Exception as e:st.error(f'Local model unavailable: {e}')
    st.subheader('Supporting documents · LibreIndex')
    st.caption('Documents provide cited context. They do not import ledger transactions or establish numerical totals. Upload text-based PDFs; scanned statements require OCR first.')
    doc=st.file_uploader('Receipt / statement / invoice',type=['pdf','txt','md'],key='doc')
    if doc and st.button('Save document'):
        (DATA/'documents'/Path(doc.name).name).write_bytes(doc.getvalue());st.success('Saved locally')
    embedding=st.text_input('Local embedding model','embeddinggemma')
    if st.button('Index supporting documents'):
        try:
            with st.spinner('Indexing locally…'):index=ai.documents(DATA/'documents',model,embedding).index()
            st.json(index.report.model_dump())
        except Exception as e:st.error(str(e))
    dq=st.text_input('Question about documents')
    if st.button('Ask documents'):
        try:
            with st.spinner('Searching locally…'):answer=ai.documents(DATA/'documents',model,embedding).ask(dq)
            st.write(answer.text)
            if answer.warning:st.warning(answer.warning)
            for citation in answer.citations:
                with st.expander(citation.location):st.write(citation.excerpt)
        except Exception as e:st.error(str(e))
