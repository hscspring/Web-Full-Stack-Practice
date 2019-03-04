import {
    Input, Form,
} from 'antd';
import React from 'react';
import axios from 'axios';
import './App.css';

const Search = Input.Search;
// 本地开发时用
// const generateUrl = "http://127.0.0.1:8000/api/generate/";
// 正式部署时用
const generateUrl = "https://naivegenerator.com/api/generate/";

const TextDisplay = props => {
    const {text} = props;
    return (<div className="App-text">
        <span>{text}</span>
    </div>)
}

class GenerateText extends React.Component {
    constructor() {
        super()
        this.state = {
            text: ''
        }
    }

    handleGenerate = (query) => {
        axios.post(generateUrl, {
            query: query
        }).then(res => {
            // 后端创建的错误码
            if (res.data === 10000) {
                alert('生成失败！请稍后重试。');
                return;
            }
            if (res.status === 200) {
                this.setState({ text: res.data.text })
            } else {
                alert('生成失败！请稍后重试。');
            }
        });
    }

    render() {
        return (
            <div>
                <div className="App-generate">
                    <Search 
                        placeholder="输入 query"
                        enterButton="生成"
                        size="large"
                        style={{ width: 300 }}
                        onSearch={this.handleGenerate}
                    />
                </div>
                <div>
                    <TextDisplay {...this.state} />
                </div>
            </div>
            );
    }
}

const WrappedGenerateText = Form.create()(GenerateText);
export default WrappedGenerateText;
