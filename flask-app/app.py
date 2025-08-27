import logging
import calendar
import sqlite3
import os
from datetime import datetime, timedelta
from flask import Flask, request, render_template, jsonify, Response, url_for
from flask_httpauth import HTTPBasicAuth
from pymongo import MongoClient
from pymongo.errors import PyMongoError
from bson.objectid import ObjectId
import csv
from io import StringIO
from dotenv import load_dotenv

logging.basicConfig(level=logging.INFO)

app = Flask(__name__)
auth = HTTPBasicAuth()

USER_DATA = {
    "mygpt": "5913#gpt"
}

@auth.verify_password
def verify_password(username, password):
    if username in USER_DATA and USER_DATA.get(username) == password:
        return username
    return None

# MongoDB connection
client = MongoClient("mongodb://mongodb:27017/")
db = client["LibreChat"]
transactions_collection = db["transactions"]
users_collection = db["users"]

def get_default_date_range():
    now = datetime.now()
    first_of_month = datetime(now.year, now.month, 1)
    last_of_month = datetime(
        now.year, now.month,
        calendar.monthrange(now.year, now.month)[1],
        23, 59, 59
    )
    return first_of_month, last_of_month

def get_date_range_for_code(range_code):
    now = datetime.now().replace(microsecond=0)
    if range_code == 'last_month':
        first_of_current_month = datetime(now.year, now.month, 1)
        last_of_last_month = first_of_current_month - timedelta(days=1)
        first_of_last_month = datetime(last_of_last_month.year, last_of_last_month.month, 1)
        start_time = first_of_last_month
        end_time = datetime(last_of_last_month.year, last_of_last_month.month, last_of_last_month.day, 23, 59, 59)
    elif range_code == 'last24':
        start_time = now - timedelta(days=1)
        end_time = now
    elif range_code == 'last7':
        start_time = (now - timedelta(days=7)).replace(hour=0, minute=0, second=0)
        end_time = now.replace(hour=23, minute=59, second=59)
    elif range_code == 'current_month':
        start_time = datetime(now.year, now.month, 1)
        end_day = calendar.monthrange(now.year, now.month)[1]
        end_time = datetime(now.year, now.month, end_day, 23, 59, 59)
    elif range_code == 'last30':
        start_time = (now - timedelta(days=30)).replace(hour=0, minute=0, second=0)
        end_time = now.replace(hour=23, minute=59, second=59)
    elif range_code == 'last60':
        start_time = (now - timedelta(days=60)).replace(hour=0, minute=0, second=0)
        end_time = now.replace(hour=23, minute=59, second=59)
    elif range_code == 'last90':
        start_time = (now - timedelta(days=90)).replace(hour=0, minute=0, second=0)
        end_time = now.replace(hour=23, minute=59, second=59)
    elif range_code == 'all_time':
        start_time = datetime(1900, 1, 1, 0, 0, 0)
        end_time = now.replace(hour=23, minute=59, second=59)
    else:
        start_time, end_time = get_default_date_range()
    return start_time, end_time

def generate_report(start_time, end_time):
    all_users = list(users_collection.find({}))

    transaction_pipeline = [
        {
            '$match': {
                'createdAt': {'$gte': start_time, '$lte': end_time}
            }
        },
        {
            '$group': {
                '_id': '$user',
                'conversations': {'$addToSet': '$conversationId'},
                'messages': {'$sum': 1},
                'input_tokens': {
                    '$sum': {
                        '$cond': [
                            {'$eq': ['$tokenType', 'prompt']}, {'$abs': '$rawAmount'}, 0
                        ]
                    }
                },
                'output_tokens': {
                    '$sum': {
                        '$cond': [
                            {'$eq': ['$tokenType', 'completion']}, {'$abs': '$rawAmount'}, 0
                        ]
                    }
                },
                'input_cost': {
                    '$sum': {
                        '$cond': [
                            {'$eq': ['$tokenType', 'prompt']},
                            {'$divide': [{'$multiply': [{'$abs': '$rawAmount'}, '$rate']}, 1000000]},
                            0
                        ]
                    }
                },
                'output_cost': {
                    '$sum': {
                        '$cond': [
                            {'$eq': ['$tokenType', 'completion']},
                            {'$divide': [{'$multiply': [{'$abs': '$rawAmount'}, '$rate']}, 1000000]},
                            0
                        ]
                    }
                }
            }
        }
    ]
    transaction_results = list(transactions_collection.aggregate(transaction_pipeline))

    file_pipeline = [
        {
            '$match': {
                'createdAt': {'$gte': start_time, '$lte': end_time}
            }
        },
        {
            '$group': {
                '_id': '$user',
                'file_count': {'$sum': 1},
                'file_size': {'$sum': '$bytes'}
            }
        }
    ]
    file_results = list(db['files'].aggregate(file_pipeline))

    transaction_data_map = {str(r['_id']): r for r in transaction_results}
    file_data_map = {str(r['_id']): r for r in file_results}

    report_data = []
    totals = {
        'conversations': 0,
        'messages': 0,
        'input_tokens': 0,
        'output_tokens': 0,
        'input_cost': 0.0,
        'output_cost': 0.0,
        'total_cost': 0.0,
        'file_count': 0,
        'file_size': 0
    }
    total_users = len(all_users)
    now = datetime.now()

    for user in all_users:
        user_id = str(user.get('_id'))
        user_name = user.get('name', 'N/A')
        email = user.get('email', 'N/A')
        transactions = transaction_data_map.get(user_id, {})
        files = file_data_map.get(user_id, {})

        conversations = len(transactions.get('conversations', []))
        messages = transactions.get('messages', 0)
        input_tokens = transactions.get('input_tokens', 0)
        output_tokens = transactions.get('output_tokens', 0)
        input_cost = transactions.get('input_cost', 0.0)
        output_cost = transactions.get('output_cost', 0.0)
        total_cost = input_cost + output_cost
        file_count = files.get('file_count', 0)
        file_size = files.get('file_size', 0) / (1024 * 1024)

        totals['conversations'] += conversations
        totals['messages'] += messages
        totals['input_tokens'] += input_tokens
        totals['output_tokens'] += output_tokens
        totals['input_cost'] += input_cost
        totals['output_cost'] += output_cost
        totals['total_cost'] += total_cost
        totals['file_count'] += file_count
        totals['file_size'] += file_size

        last_transaction = transactions_collection.find({'user': ObjectId(user_id)}).sort('createdAt', -1).limit(1)
        last_usage = None
        for lt in last_transaction:
            last_usage = lt.get('createdAt')
            break
        if last_usage:
            last_usage_str = last_usage.strftime('%Y-%m-%d %H:%M:%S')
            days_since_last = (now - last_usage).days
            last_usage_display = f"{last_usage_str} (today)" if days_since_last == 0 else f"{last_usage_str} ({days_since_last} days)"
        else:
            last_usage_display = "(never)"
        report_data.append({
            'user_name': user_name,
            'email': email,
            'last_usage_display': last_usage_display,
            'conversations': conversations,
            'messages': messages,
            'input_tokens': input_tokens,
            'output_tokens': output_tokens,
            'input_cost': input_cost,
            'output_cost': output_cost,
            'total_cost': total_cost,
            'file_count': file_count,
            'file_size': file_size
        })
    return report_data, totals, total_users

@app.route('/download_report', methods=['GET'])
@auth.login_required
def download_report():
    try:
        range_code = request.args.get('range')
        sort_by = request.args.get('sort_by', 'total_cost')
        order = request.args.get('order', 'desc')
        start_time, end_time = get_date_range_for_code(range_code)
        report_data, totals, total_users = generate_report(start_time, end_time)
        ascending = (order == 'asc')
        report_data.sort(key=lambda x: x.get(sort_by, 0), reverse=not ascending)
        si = StringIO()
        cw = csv.writer(si)
        cw.writerow(['User Name', 'Email', 'Last Use', 'Conversations', 'Messages', 'Files', 'File Size (MB)', 'Input Tokens', 'Output Tokens', 'Input Cost ($)', 'Output Cost ($)', 'Total Cost ($)'])
        for row in report_data:
            cw.writerow([
                row['user_name'],
                row['email'],
                row['last_usage_display'],
                row['conversations'],
                row['messages'],
                row['file_count'],
                f"{row['file_size']:.2f}",
                row['input_tokens'],
                row['output_tokens'],
                f"{row['input_cost']:.2f}",
                f"{row['output_cost']:.2f}",
                f"{row['total_cost']:.2f}"
            ])
        output = si.getvalue()
        filename = f"mygpt_report_{start_time.strftime('%Y-%m-%d-%H%M')}_{end_time.strftime('%Y-%m-%d-%H%M')}.csv"
        return Response(
            output,
            mimetype="text/csv",
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )
    except Exception as e:
        logging.error(f"Failed to generate CSV: {str(e)}")
        return jsonify({'error': 'Failed to generate CSV report.'}), 500

@app.route('/dashboard', methods=['GET'])
@auth.login_required
def reporting_dashboard():
    range_code = request.args.get('range', 'last30')
    sort_by = request.args.get('sort_by', 'total_cost')
    order = request.args.get('order', 'desc')
    start_time, end_time = get_date_range_for_code(range_code)
    logging.info(f"Generating report from {start_time} to {end_time}")
    try:
        report_data, totals, total_users = generate_report(start_time, end_time)
        if total_users > 0:
            average_data = {
                'conversations': totals['conversations'] / total_users,
                'messages': totals['messages'] / total_users,
                'input_tokens': totals['input_tokens'] / total_users,
                'output_tokens': totals['output_tokens'] / total_users,
                'input_cost': totals['input_cost'] / total_users,
                'output_cost': totals['output_cost'] / total_users,
                'total_cost': totals['total_cost'] / total_users,
                'file_count': totals['file_count'] / total_users,
                'file_size': totals['file_size'] / total_users
            }
        else:
            average_data = {key: 0 for key in ['conversations', 'messages', 'input_tokens', 'output_tokens', 'input_cost', 'output_cost', 'total_cost', 'file_count', 'file_size']}
        ascending = (order == 'asc')
        if sort_by == 'last_usage':
            report_data.sort(key=lambda x: (
                x.get(sort_by) is not None,
                x.get(sort_by) if x.get(sort_by) is not None else (datetime.max if ascending else datetime.min)
            ), reverse=not ascending)
        else:
            report_data.sort(key=lambda x: x.get(sort_by, 0), reverse=not ascending)
        return render_template(
            'dashboard.html',
            report_data=report_data,
            totals=totals,
            average_data=average_data,
            total_users=total_users,
            start_time=start_time,
            end_time=end_time,
            sort_by=sort_by,
            order=order,
            range_code=range_code
        )
    except PyMongoError as e:
        logging.error(f"Database error: {str(e)}")
        return render_template('error.html', message="There was an issue connecting to the database."), 500
    except Exception as e:
        logging.error(f"An unexpected error occurred: {str(e)}")
        return render_template('error.html', message="An unexpected error occurred."), 500

@app.route('/metrics_dashboard')
@auth.login_required
def metrics_dashboard():
    range_code = request.args.get('range', 'last30')
    start_time, end_time = get_date_range_for_code(range_code)
    try:
        report_data, totals, total_users = generate_report(start_time, end_time)
        if total_users > 0:
            average_data = {
                'conversations': totals['conversations'] / total_users,
                'messages': totals['messages'] / total_users,
                'input_tokens': totals['input_tokens'] / total_users,
                'output_tokens': totals['output_tokens'] / total_users,
                'input_cost': totals['input_cost'] / total_users,
                'output_cost': totals['output_cost'] / total_users,
                'total_cost': totals['total_cost'] / total_users,
                'file_count': totals['file_count'] / total_users,
                'file_size': totals['file_size'] / total_users
            }
        else:
            average_data = {key: 0 for key in ['conversations', 'messages', 'input_tokens', 'output_tokens', 'input_cost', 'output_cost', 'total_cost', 'file_count', 'file_size']}
        return render_template(
            'metrics.html',
            report_data=report_data,
            totals=totals,
            average_data=average_data,
            total_users=total_users,
            start_time=start_time,
            end_time=end_time,
            range_code=range_code
        )
    except PyMongoError as e:
        logging.error(f"Database error: {str(e)}")
        return render_template('error.html', message="There was an issue connecting to the database."), 500
    except Exception as e:
        logging.error(f"An unexpected error occurred: {str(e)}")
        return render_template('error.html', message="An unexpected error occurred."), 500

@app.route('/metrics', methods=['GET'])
@auth.login_required
def metrics():
    try:
        range_code = request.args.get('range', 'last30')
        start_time, end_time = get_date_range_for_code(range_code)
        # Calculate monthly usage data for the last 12 months using aggregation,
        # independent of the selected report range.
        from dateutil.relativedelta import relativedelta
        end_now = datetime.now()
        twelve_months_ago = end_now.replace(day=1) - relativedelta(months=11)
        monthly_usage_pipeline = [
            { '$match': { 'createdAt': {'$gte': twelve_months_ago, '$lte': end_now} } },
            { '$group': {
                  '_id': {
                      'year': { '$year': '$createdAt' },
                      'month': { '$month': '$createdAt' }
                  },
                  'users': { '$addToSet': '$user' },
                  'message_count': { '$sum': 1 }
              } },
            { '$project': {
                  'month': {
                      '$concat': [
                          { '$toString': '$_id.year' },
                          "-",
                          { '$cond': [
                              { '$lt': ['$_id.month', 10] },
                              { '$concat': ["0", { '$toString': '$_id.month' }] },
                              { '$toString': '$_id.month' }
                          ] }
                      ]
                  },
                  'user_count': { '$size': '$users' },
                  'message_count': 1,
                  '_id': 0
              } },
            { '$sort': { 'month': 1 } }
        ]
        monthly_usage_data = list(transactions_collection.aggregate(monthly_usage_pipeline))
        monthly_usage_data.sort(key=lambda x: x['month'])

        # Calculate daily, weekly, and monthly active users
        daily_active_pipeline = [
            { '$match': { 'createdAt': {'$gte': start_time, '$lte': end_time} } },
            { '$group': { '_id': { 'day': {'$dateToString': {'format': '%Y-%m-%d', 'date': '$createdAt'}}, 'user': '$user' } } },
            { '$group': { '_id': '$_id.day', 'users': {'$sum': 1} } }
        ]
        daily_active_results = list(transactions_collection.aggregate(daily_active_pipeline))
        dau = sum(day['users'] for day in daily_active_results) / len(daily_active_results) if daily_active_results else 0

        weekly_active_pipeline = [
            { '$match': { 'createdAt': {'$gte': start_time, '$lte': end_time} } },
            { '$group': { '_id': { 'week': {'$dateToString': {'format': '%Y-%U', 'date': '$createdAt'}}, 'user': '$user' } } },
            { '$group': { '_id': '$_id.week', 'users': {'$sum': 1} } }
        ]
        weekly_active_results = list(transactions_collection.aggregate(weekly_active_pipeline))
        wau = sum(week['users'] for week in weekly_active_results) / len(weekly_active_results) if weekly_active_results else 0

        monthly_active_pipeline = [
            { '$match': { 'createdAt': {'$gte': start_time, '$lte': end_time} } },
            { '$group': { '_id': { 'month': {'$dateToString': {'format': '%Y-%m', 'date': '$createdAt'}}, 'user': '$user' } } },
            { '$group': { '_id': '$_id.month', 'users': {'$sum': 1} } }
        ]
        monthly_active_results = list(transactions_collection.aggregate(monthly_active_pipeline))
        mau = sum(month['users'] for month in monthly_active_results) / len(monthly_active_results) if monthly_active_results else 0

        # Peak usage times (top 10)
        days_of_week = ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday']
        usage_pipeline = [
            { '$match': { 'createdAt': {'$gte': start_time, '$lte': end_time} } },
            { '$group': { '_id': { 'hour': {'$hour': '$createdAt'}, 'day': {'$dayOfWeek': '$createdAt'} }, 'count': {'$sum': 1} } },
            { '$sort': { 'count': -1 } }
        ]
        peak_usage_raw = list(transactions_collection.aggregate(usage_pipeline))
        peak_usage = [
            { 'day': days_of_week[item['_id']['day'] - 1], 'hour': item['_id']['hour'], 'time': f"{item['_id']['hour']}:00", 'count': item['count'] }
            for item in peak_usage_raw[:10]
        ]

        # Conversation and token metrics
        conversation_pipeline = [
            { '$match': { 'createdAt': {'$gte': start_time, '$lte': end_time}, 'conversationId': {'$exists': True, '$ne': None} } },
            { '$group': { '_id': '$conversationId', 'message_count': {'$sum': 1},
                           'input_tokens': { '$sum': { '$cond': [ {'$eq': ['$tokenType', 'prompt']}, {'$abs': '$rawAmount'}, 0 ] } },
                           'output_tokens': { '$sum': { '$cond': [ {'$eq': ['$tokenType', 'completion']}, {'$abs': '$rawAmount'}, 0 ] } }
                         }
            }
        ]
        conversation_lengths = list(transactions_collection.aggregate(conversation_pipeline))
        total_conversations = len(conversation_lengths)
        if total_conversations > 0:
            avg_conversation_length = sum(c['message_count'] for c in conversation_lengths) / total_conversations
            total_input_tokens = sum(c['input_tokens'] for c in conversation_lengths)
            total_output_tokens = sum(c['output_tokens'] for c in conversation_lengths)
            token_efficiency = total_output_tokens / total_input_tokens if total_input_tokens > 0 else 0
        else:
            avg_conversation_length = 0
            token_efficiency = 0

        # Feature utilization: model usage
        feature_pipeline = [
            { '$match': { 'createdAt': {'$gte': start_time, '$lte': end_time}, 'model': {'$exists': True, '$ne': None} } },
            { '$group': { '_id': '$model', 'usage_count': {'$sum': 1}, 'total_tokens': {'$sum': {'$abs': '$rawAmount'}} } },
            { '$sort': { 'usage_count': -1 } }
        ]
        model_usage = list(transactions_collection.aggregate(feature_pipeline))
        # Cost by Model Calculation
        cost_by_model_pipeline = [
            { '$match': { 'createdAt': {'$gte': start_time, '$lte': end_time}, 'model': {'$exists': True, '$ne': None} } },
            { '$group': {
                '_id': '$model',
                'total_input_cost': {
                    '$sum': {
                        '$cond': [
                            {'$eq': ['$tokenType', 'prompt']},
                            {'$divide': [{'$multiply': [{'$abs': '$rawAmount'}, '$rate']}, 1000000]},
                            0
                        ]
                    }
                },
                'total_output_cost': {
                    '$sum': {
                        '$cond': [
                            {'$eq': ['$tokenType', 'completion']},
                            {'$divide': [{'$multiply': [{'$abs': '$rawAmount'}, '$rate']}, 1000000]},
                            0
                        ]
                    }
                }
            }},
            { '$project': {
                '_id': 1,
                'total_cost': { '$add': [ { '$ifNull': ['$total_input_cost', 0] }, { '$ifNull': ['$total_output_cost', 0] } ] }
            }},
            { '$sort': { 'total_cost': -1 } }
        ]
        cost_by_model = list(transactions_collection.aggregate(cost_by_model_pipeline))

        # Daily usage data for chart
        daily_usage_pipeline = [
            { '$match': { 'createdAt': {'$gte': start_time, '$lte': end_time} } },
            { '$group': { '_id': { 'date': {'$dateToString': {'format': '%Y-%m-%d', 'date': '$createdAt'}}, 'user': '$user' }, 'message_count': {'$sum': 1} } },
            { '$group': { '_id': '$_id.date', 'user_count': {'$sum': 1}, 'message_count': {'$sum': '$message_count'} } },
            { '$sort': { '_id': 1 } }
        ]
        daily_usage_data = list(transactions_collection.aggregate(daily_usage_pipeline))
        formatted_daily_usage = []
        for day in daily_usage_data:
            formatted_daily_usage.append({ 'date': day['_id'], 'user_count': day['user_count'], 'message_count': day['message_count'] })

        # Weekly usage data for chart
        weekly_usage_pipeline = [
            { '$match': { 'createdAt': {'$gte': start_time, '$lte': end_time} } },
            { '$group': { '_id': { 'week': {'$dateToString': {'format': '%Y-%U', 'date': '$createdAt'}}, 'user': '$user' }, 'message_count': {'$sum': 1} } },
            { '$group': { '_id': '$_id.week', 'user_count': {'$sum': 1}, 'message_count': {'$sum': '$message_count'} } },
            { '$sort': { '_id': 1 } }
        ]
        weekly_usage_data = list(transactions_collection.aggregate(weekly_usage_pipeline))
        formatted_weekly_usage = []
        for week in weekly_usage_data:
            formatted_weekly_usage.append({ 'week': week['_id'], 'user_count': week['user_count'], 'message_count': week['message_count'] })

        # Compute hourly usage data
        hourly_usage_pipeline = [
            { '$match': { 'createdAt': {'$gte': start_time, '$lte': end_time} } },
            { '$group': { '_id': { 'hour': { '$hour': '$createdAt' } }, 'count': {'$sum': 1} } }
        ]
        hourly_usage_data = [0] * 24
        for doc in list(transactions_collection.aggregate(hourly_usage_pipeline)):
            hour = doc['_id']['hour']
            hourly_usage_data[hour] = doc['count']

        # Calculate user recency (days since last use)
        user_recency_pipeline = [
            { '$match': { 'createdAt': {'$exists': True} } },
            { '$sort': { 'createdAt': -1 } },
            { '$group': {
                '_id': '$user',
                'last_usage': { '$first': '$createdAt' }
            }},
            { '$project': {
                'days_since': {
                    '$ceil': {
                        '$divide': [
                            { '$subtract': [datetime.now(), '$last_usage'] },
                            1000 * 60 * 60 * 24  # Convert ms to days
                        ]
                    }
                }
            }}
        ]
        user_recency_data = list(transactions_collection.aggregate(user_recency_pipeline))
        
        # Create histogram buckets (0-60 days + >60)
        recency_histogram = [0] * 61  # 0-60 days
        recency_histogram.append(0)   # >60 days bucket
        
        # Collect raw values for statistics calculation
        recency_raw_values = []
        
        for user in user_recency_data:
            days = user.get('days_since', 0)
            recency_raw_values.append(days)
            if days > 60:
                recency_histogram[61] += 1  # Add to >60 bucket
            else:
                try:
                    recency_histogram[int(days)] += 1
                except (ValueError, IndexError):
                    # Handle any potential errors with the data
                    pass
        
        # Calculate statistics for user recency
        recency_stats = {}
        if recency_raw_values:
            import numpy as np
            recency_stats = {
                'mean': float(np.mean(recency_raw_values)),
                'median': float(np.median(recency_raw_values)),
                'std_dev': float(np.std(recency_raw_values))
            }
        else:
            recency_stats = {
                'mean': 0,
                'median': 0,
                'std_dev': 0
            }
                    
        # Calculate messages per chat histogram
        messages_per_chat_pipeline = [
            { '$match': { 'createdAt': {'$gte': start_time, '$lte': end_time}, 'conversationId': {'$exists': True, '$ne': None} } },
            { '$group': { '_id': '$conversationId', 'message_count': {'$sum': 1} } }
        ]
        messages_per_chat_data = list(transactions_collection.aggregate(messages_per_chat_pipeline))
        
        # Create histogram buckets (0-20 messages + >20)
        messages_per_chat_histogram = [0] * 21  # 0-20 messages
        messages_per_chat_histogram.append(0)   # >20 messages bucket
        
        # Collect raw values for statistics calculation
        messages_per_chat_raw_values = []
        
        for chat in messages_per_chat_data:
            count = chat.get('message_count', 0)
            messages_per_chat_raw_values.append(count)
            if count > 20:
                messages_per_chat_histogram[21] += 1  # Add to >20 bucket
            else:
                messages_per_chat_histogram[count] += 1
        
        # Calculate statistics for messages per chat
        messages_per_chat_stats = {}
        if messages_per_chat_raw_values:
            import numpy as np
            messages_per_chat_stats = {
                'mean': float(np.mean(messages_per_chat_raw_values)),
                'median': float(np.median(messages_per_chat_raw_values)),
                'std_dev': float(np.std(messages_per_chat_raw_values))
            }
        else:
            messages_per_chat_stats = {
                'mean': 0,
                'median': 0,
                'std_dev': 0
            }
                
        # Calculate messages per session histogram (30-minute inactivity threshold)
        # First, get all transactions sorted by user and time
        user_transactions_pipeline = [
            { '$match': { 'createdAt': {'$gte': start_time, '$lte': end_time} } },
            { '$sort': { 'user': 1, 'createdAt': 1 } },
            { '$group': {
                '_id': '$user',
                'transactions': { 
                    '$push': {
                        'createdAt': '$createdAt'
                    }
                }
            }}
        ]
        user_transactions = list(transactions_collection.aggregate(user_transactions_pipeline))
        
        # Process each user's transactions to identify sessions
        messages_per_session_histogram = [0] * 21  # 0-20 messages
        messages_per_session_histogram.append(0)   # >20 messages bucket
        
        # Collect raw values for statistics calculation
        messages_per_session_raw_values = []
        
        for user_data in user_transactions:
            transactions = user_data.get('transactions', [])
            if not transactions:
                continue
                
            # Initialize the first session
            current_session_start = transactions[0]['createdAt']
            current_session_messages = 1
            
            # Process remaining transactions
            for i in range(1, len(transactions)):
                current_time = transactions[i]['createdAt']
                time_diff = (current_time - transactions[i-1]['createdAt']).total_seconds() / 60
                
                # If time difference > 30 minutes, end current session and start a new one
                if time_diff > 30:
                    # Record the completed session
                    messages_per_session_raw_values.append(current_session_messages)
                    if current_session_messages > 20:
                        messages_per_session_histogram[21] += 1
                    else:
                        messages_per_session_histogram[current_session_messages] += 1
                    
                    # Start a new session
                    current_session_start = current_time
                    current_session_messages = 1
                else:
                    # Continue the current session
                    current_session_messages += 1
            
            # Record the last session
            messages_per_session_raw_values.append(current_session_messages)
            if current_session_messages > 20:
                messages_per_session_histogram[21] += 1
            else:
                messages_per_session_histogram[current_session_messages] += 1
        
        # Calculate statistics for messages per session
        messages_per_session_stats = {}
        if messages_per_session_raw_values:
            import numpy as np
            messages_per_session_stats = {
                'mean': float(np.mean(messages_per_session_raw_values)),
                'median': float(np.median(messages_per_session_raw_values)),
                'std_dev': float(np.std(messages_per_session_raw_values))
            }
        else:
            messages_per_session_stats = {
                'mean': 0,
                'median': 0,
                'std_dev': 0
            }
        
        response = {
            "engagement": {"DAU": dau, "WAU": wau, "MAU": mau},
            "insights": {
                "hourly_usage": hourly_usage_data,
                "peak_usage": peak_usage,
                "daily_usage_data": formatted_daily_usage,
                "weekly_usage_data": formatted_weekly_usage,
                "monthly_usage_data": monthly_usage_data,
                "user_recency_histogram": recency_histogram,
                "user_recency_stats": recency_stats,
                "messages_per_chat_histogram": messages_per_chat_histogram,
                "messages_per_chat_stats": messages_per_chat_stats,
                "messages_per_session_histogram": messages_per_session_histogram,
                "messages_per_session_stats": messages_per_session_stats
            },
            "behavior_trends": {"avg_conversation_length": avg_conversation_length, "token_efficiency": token_efficiency, "model_usage": model_usage, "cost_by_model": cost_by_model},
            "totals": {}
        }
        return jsonify(response)
    except Exception as e:
        logging.error(f"Failed to generate metrics: {str(e)}")
        return jsonify({'error': f'Failed to generate metrics report: {str(e)}'}), 500

# Load environment variables
load_dotenv()

# SQLite database path for message categories
SQLITE_DB_PATH = os.getenv("SQLITE_DB_PATH", "message_categories.db")

@app.route('/categories', methods=['GET'])
@auth.login_required
def categories_dashboard():
    """Display the message categories dashboard."""
    try:
        # Connect to SQLite database
        conn = sqlite3.connect(SQLITE_DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # Get category statistics
        cursor.execute(
            """
            SELECT category, COUNT(*) as count
            FROM message_categories
            GROUP BY category
            ORDER BY count DESC
            """
        )
        
        category_counts = cursor.fetchall()
        
        # Get total count
        cursor.execute("SELECT COUNT(*) FROM message_categories")
        total_count = cursor.fetchone()[0]
        
        # Format data for template
        categories = []
        category_data = {"labels": [], "values": []}
        
        for row in category_counts:
            category = row['category']
            count = row['count']
            percentage = (count / total_count) * 100 if total_count > 0 else 0
            
            categories.append({
                "name": category,
                "count": count,
                "percentage": percentage
            })
            
            category_data["labels"].append(category)
            category_data["values"].append(count)
        
        # Get recent categorized messages
        cursor.execute(
            """
            SELECT message_id as id, category, confidence, 
                   substr(message_text, 1, 50) || '...' as preview, 
                   processed_at
            FROM message_categories
            ORDER BY processed_at DESC
            LIMIT 20
            """
        )
        
        recent_messages = [dict(row) for row in cursor.fetchall()]
        
        # Close connection
        conn.close()
        
        return render_template(
            'categories.html',
            categories=categories,
            category_data=category_data,
            recent_messages=recent_messages,
            total_count=total_count
        )
        
    except Exception as e:
        logging.error(f"Error displaying categories dashboard: {str(e)}")
        return render_template('error.html', message="An error occurred while retrieving category data."), 500

@app.route('/category/<category_name>', methods=['GET'])
@auth.login_required
def category_details(category_name):
    """Display all messages in a specific category."""
    try:
        # Connect to SQLite database
        conn = sqlite3.connect(SQLITE_DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # Get category count
        cursor.execute(
            """
            SELECT COUNT(*) as count
            FROM message_categories
            WHERE category = ?
            """,
            (category_name,)
        )
        
        category_count = cursor.fetchone()['count']
        
        # Get all messages in this category
        cursor.execute(
            """
            SELECT message_id as id, message_text, confidence, processed_at
            FROM message_categories
            WHERE category = ?
            ORDER BY processed_at DESC
            """,
            (category_name,)
        )
        
        category_messages = [dict(row) for row in cursor.fetchall()]
        
        # Close connection
        conn.close()
        
        return render_template(
            'category_details.html',
            category_name=category_name,
            category_count=category_count,
            messages=category_messages
        )
        
    except Exception as e:
        logging.error(f"Error displaying category details: {str(e)}")
        return render_template('error.html', message="An error occurred while retrieving category data."), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8082, debug=True)
